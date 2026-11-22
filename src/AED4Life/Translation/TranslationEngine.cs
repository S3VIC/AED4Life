using System.Data;
using System.Globalization;
using System.Linq.Expressions;
using System.Text;
using AED4Life.DataModel;
using AED4Life.DataModel.DTOs;
using AED4Life.DataModel.Entities;
using AED4Life.Trananslation;
using CsvHelper;
using CsvHelper.Configuration;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.ChangeTracking;
using Microsoft.EntityFrameworkCore.Metadata;

namespace AED4Life.Translation;

public sealed class TranslationEngine(AED4LifeDbContext database) {
	private static readonly IReadOnlyDictionary<String, Type> Tables = new Dictionary<String, Type>(StringComparer.Ordinal) {
		["Cities"] = typeof(City),
		["Streets"] = typeof(Street),
		["PostalCodes"] = typeof(PostalCode),
		["Addresses"] = typeof(Address),
		["AEDOwners"] = typeof(AEDOwner),
		["AEDs"] = typeof(AED)
	};

	public async Task<CsvImportResponse> ImportAsync(
		Stream stream, TranslationProfile profile, CancellationToken cancellationToken) {
		using StreamReader reader = new(stream, new UTF8Encoding(false, true),
			detectEncodingFromByteOrderMarks: false, leaveOpen: true);
		if (reader.Peek() == '\uFEFF') {
			reader.Read();
		}
		using CsvReader csv = new(reader, new CsvConfiguration(CultureInfo.InvariantCulture) {
			Delimiter = ",",
			HasHeaderRecord = true,
			DetectColumnCountChanges = true,
			ExceptionMessagesContainRawData = false
		});
		if (!await csv.ReadAsync()) {
			throw new CsvImportException("file", "The CSV must contain a header and at least one data row.");
		}
		csv.ReadHeader();
		String[] headers = csv.HeaderRecord ?? [];
		if (headers.Length == 0 || headers.Any(String.IsNullOrWhiteSpace)
			|| headers.Distinct(StringComparer.Ordinal).Count() != headers.Length) {
			throw new CsvImportException("file", "CSV headers must be nonblank and unique (case-sensitive).");
		}
		List<ColumnMapping> mappings = BindColumns(profile, headers);
		Dictionary<String, CsvImportTableResult> counts = mappings.Select(mapping => mapping.Table)
			.Distinct().ToDictionary(table => table, _ => new CsvImportTableResult(0, 0), StringComparer.Ordinal);

		// Serializable reads protect natural-key upserts even where the schema has no unique index.
		await using var transaction = await database.Database.BeginTransactionAsync(IsolationLevel.Serializable, cancellationToken);
		Int32 rowsProcessed = 0;
		while (await csv.ReadAsync()) {
			cancellationToken.ThrowIfCancellationRequested();
			ImportRow row = new(csv.Parser.Row, new(StringComparer.Ordinal));
			String[] fields = csv.Parser.Record ?? [];
			foreach (ColumnMapping mapping in mappings) {
				if (!row.Values.TryGetValue(mapping.Table, out Dictionary<String, Object?>? values)) {
					values = new(StringComparer.Ordinal);
					row.Values.Add(mapping.Table, values);
				}
				Object? value = ReadValue(fields[mapping.Index], mapping, row.Number);
				if (value is null && mapping.Property.ClrType == typeof(DateTime)) {
					continue;
				}
				values.Add(mapping.Property.Name, value);
			}
			await ImportRowAsync(row, counts, cancellationToken);
			database.ChangeTracker.Clear();
			rowsProcessed++;
		}
		if (rowsProcessed == 0) {
			throw new CsvImportException("file", "The CSV must contain at least one data row.");
		}
		await transaction.CommitAsync(cancellationToken);
		return new CsvImportResponse(profile.Name, rowsProcessed, counts);
	}

	private List<ColumnMapping> BindColumns(TranslationProfile profile, String[] headers) {
		if (profile.Units.Count == 0) {
			throw new CsvImportException("profile", "The translation profile has no mapping units.");
		}
		List<ColumnMapping> mappings = [];
		HashSet<String> destinations = new(StringComparer.Ordinal);
		foreach (TranslationProfileUnit unit in profile.Units.OrderBy(unit => unit.Position)) {
			Int32 index = Array.IndexOf(headers, unit.FromColumn);
			if (index < 0) {
				throw new CsvImportException("file", $"The CSV is missing the mapped header '{unit.FromColumn}'.");
			}
			String[] destination = unit.ToColumn.Split('.');
			if (destination.Length != 2 || !Tables.TryGetValue(destination[0], out Type? entityType)) {
				throw new CsvImportException("profile", $"Destination '{unit.ToColumn}' must use a supported Table.Column name.");
			}
			IProperty? property = database.Model.FindEntityType(entityType)?.FindProperty(destination[1]);
			if (property is null || property.IsPrimaryKey()) {
				throw new CsvImportException("profile", $"Destination '{unit.ToColumn}' is not an importable column. IDs are generated.");
			}
			if (!destinations.Add(unit.ToColumn)) {
				throw new CsvImportException("profile", $"Destination '{unit.ToColumn}' is mapped more than once.");
			}
			Type type = Nullable.GetUnderlyingType(property.ClrType) ?? property.ClrType;
			VariableType expected = type == typeof(String) || type == typeof(DateTime) ? VariableType.STRING
				: type == typeof(Boolean) ? VariableType.BOOLEAN
				: type == typeof(Double) ? VariableType.DOUBLE : VariableType.INTEGER;
			if (!Enum.IsDefined(unit.FromType) || unit.ToType != expected) {
				throw new CsvImportException("profile", $"Destination '{unit.ToColumn}' requires toType {expected} and a valid fromType.");
			}
			mappings.Add(new ColumnMapping(index, destination[0], property, unit.FromType, unit.ToType));
		}
		return mappings;
	}

	private static Object? ReadValue(String raw, ColumnMapping mapping, Int32 row) {
		String key = $"rows[{row}].{mapping.Table}.{mapping.Property.Name}";
		if (String.IsNullOrWhiteSpace(raw) || String.Equals(raw.Trim(), "NULL", StringComparison.OrdinalIgnoreCase)
			|| raw.Trim() == @"\N") {
			return null;
		}
		try {
			Object source = mapping.FromType switch {
				VariableType.STRING => raw,
				VariableType.INTEGER => Int64.Parse(raw, NumberStyles.Integer, CultureInfo.InvariantCulture),
				VariableType.DOUBLE => ParseDouble(raw),
				VariableType.BOOLEAN => ParseBoolean(raw),
				_ => throw new FormatException()
			};
			Object converted = mapping.ToType switch {
				VariableType.STRING => Convert.ToString(source, CultureInfo.InvariantCulture) ?? String.Empty,
				VariableType.INTEGER => ToInteger(source),
				VariableType.DOUBLE => source is String numberText ? ParseDouble(numberText) : Convert.ToDouble(source, CultureInfo.InvariantCulture),
				VariableType.BOOLEAN => ParseBoolean(Convert.ToString(source, CultureInfo.InvariantCulture) ?? String.Empty),
				_ => throw new FormatException()
			};
			Type type = Nullable.GetUnderlyingType(mapping.Property.ClrType) ?? mapping.Property.ClrType;
			if (converted is String text) {
				if (String.IsNullOrWhiteSpace(text) || (mapping.Property.GetMaxLength() is Int32 maxLength && text.Length > maxLength)) {
					throw new FormatException();
				}
				if (type == typeof(DateTime)) {
					DateTime timestamp = DateTime.Parse(text, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind);
					if (timestamp.Year < 1000) {
						throw new FormatException();
					}
					return timestamp;
				}
			}
			if (converted is Int64 integer) {
				if (mapping.Property.IsForeignKey() && integer <= 0) {
					throw new FormatException();
				}
				if (type.IsEnum) {
					Object enumValue = Enum.ToObject(type, checked((Int32)integer));
					if (!Enum.IsDefined(type, enumValue)) {
						throw new FormatException();
					}
					return enumValue;
				}
				if (type == typeof(Int32)) {
					return checked((Int32)integer);
				}
			}
			return converted;
		} catch (Exception exception) when (exception is FormatException or OverflowException) {
			throw new CsvImportException(key,
				$"The value cannot be converted from {mapping.FromType} to {mapping.Table}.{mapping.Property.Name} "
				+ $"({mapping.ToType}); check its format, length, and allowed range.");
		}
	}

	private static Double ParseDouble(String value) {
		Double number = Double.Parse(value, NumberStyles.Float, CultureInfo.InvariantCulture);
		return Double.IsFinite(number) ? number : throw new FormatException();
	}

	private static Boolean ParseBoolean(String value) => value.Trim() switch {
		"1" => true,
		"0" => false,
		String text when Boolean.TryParse(text, out Boolean boolean) => boolean,
		_ => throw new FormatException()
	};

	private static Int64 ToInteger(Object value) {
		if (value is Double number && Math.Truncate(number) != number) {
			throw new FormatException();
		}
		return Convert.ToInt64(value, CultureInfo.InvariantCulture);
	}

	private async Task ImportRowAsync(ImportRow row, Dictionary<String, CsvImportTableResult> counts, CancellationToken cancellationToken) {
		Boolean hasOwnerValues = row.Values.TryGetValue("AEDOwners", out Dictionary<String, Object?>? ownerValues)
			&& ownerValues.Values.Any(value => value is not null);
		if (row.Values.ContainsKey("AEDs") && !HasValue(row, "AEDs", nameof(AED.AddressId))
			&& !row.Values.ContainsKey("Addresses")
			&& (row.Values.ContainsKey("Cities") || row.Values.ContainsKey("Streets") || row.Values.ContainsKey("PostalCodes"))) {
			row.Values.Add("Addresses", new(StringComparer.Ordinal));
			counts.TryAdd("Addresses", new CsvImportTableResult(0, 0));
		}

		City? city = await UpsertAsync(row, "Cities", ["Name"], () => new City(), counts, cancellationToken);
		Street? street = await UpsertAsync(row, "Streets", ["Name"], () => new Street(), counts, cancellationToken);
		PostalCode? postalCode = await UpsertAsync(row, "PostalCodes", ["Code"], () => new PostalCode(), counts, cancellationToken);
		Link(row, "Cities", "Addresses", "CityId", city?.Id);
		Link(row, "Streets", "Addresses", "StreetId", street?.Id);
		Link(row, "PostalCodes", "Addresses", "PostalCodeId", postalCode?.Id);
		if (hasOwnerValues) {
			Link(row, "Cities", "AEDOwners", "CityId", city?.Id);
			Link(row, "Streets", "AEDOwners", "StreetId", street?.Id);
		}
		Address? address = await UpsertAsync(row, "Addresses", ["CityId", "StreetId", "PostalCodeId", "BuildingNumber"],
			() => new Address(), counts, cancellationToken);
		Link(row, "Addresses", "AEDs", "AddressId", address?.Id);
		String[] ownerKeys = HasValue(row, "AEDOwners", nameof(AEDOwner.RegonNumber)) ? ["RegonNumber"]
			: HasValue(row, "AEDOwners", nameof(AEDOwner.Name)) ? ["Name", "CityId", "StreetId"] : [];
		AEDOwner? owner = await UpsertAsync(row, "AEDOwners", ownerKeys, () => new AEDOwner(), counts, cancellationToken);
		Link(row, "AEDOwners", "AEDs", "OwnerId", owner?.Id);
		String[] aedKeys = HasValue(row, "AEDs", nameof(AED.SerialNumber)) ? ["SerialNumber"]
			: HasValue(row, "AEDs", nameof(AED.Latitude)) && HasValue(row, "AEDs", nameof(AED.Longitude))
				? ["Latitude", "Longitude", "AddressId"] : [];
		await UpsertAsync(row, "AEDs", aedKeys,
			() => new AED { Created = DateTime.UtcNow, LastUpdated = DateTime.UtcNow }, counts, cancellationToken);
	}

	private static Boolean HasValue(ImportRow row, String table, String column) =>
		row.Values.TryGetValue(table, out Dictionary<String, Object?>? values)
		&& values.TryGetValue(column, out Object? value) && value is not null;

	private static void Link<T>(ImportRow row, String source, String table, String column, T? id) where T : struct {
		if (!row.Values.ContainsKey(source) || !row.Values.TryGetValue(table, out Dictionary<String, Object?>? values)) {
			return;
		}
		if (values.TryGetValue(column, out Object? explicitId) && explicitId is not null) {
			if (id is not null && !Equals(explicitId, id.Value)) {
				throw new CsvImportException($"rows[{row.Number}].{table}.{column}",
					"The explicit foreign key conflicts with the related record mapped in this row.");
			}
			return;
		}
		values[column] = id;
	}

	private async Task<TEntity?> UpsertAsync<TEntity>(ImportRow row, String table, String[] keys,
		Func<TEntity> create, Dictionary<String, CsvImportTableResult> counts, CancellationToken cancellationToken) where TEntity : class {
		if (!row.Values.TryGetValue(table, out Dictionary<String, Object?>? values)) {
			return null;
		}
		if (table != "AEDs" && values.Values.All(value => value is null)) {
			return null;
		}
		ParameterExpression parameter = Expression.Parameter(typeof(TEntity), "entity");
		Expression? predicate = null;
		foreach (String key in keys) {
			values.TryGetValue(key, out Object? value);
			MemberExpression property = Expression.Property(parameter, key);
			Expression constant = value is null ? Expression.Constant(null, property.Type)
				: Expression.Convert(Expression.Constant(value), property.Type);
			Expression equals = Expression.Equal(property, constant);
			predicate = predicate is null ? equals : Expression.AndAlso(predicate, equals);
		}
		List<TEntity> matches = predicate is null ? [] : await database.Set<TEntity>()
			.Where(Expression.Lambda<Func<TEntity, Boolean>>(predicate, parameter)).Take(2).ToListAsync(cancellationToken);
		if (matches.Count > 1) {
			throw new CsvImportException($"rows[{row.Number}].{table}",
				"Multiple existing records match this row. Resolve the ambiguous matching key before importing.");
		}
		Boolean inserted = matches.Count == 0;
		TEntity entity = inserted ? create() : matches[0];
		EntityEntry<TEntity> entry = database.Entry(entity);
		if (inserted) {
			foreach (IProperty property in entry.Metadata.GetProperties()) {
				if (property.ValueGenerated == ValueGenerated.Never && !property.IsNullable
					&& !(entity is AED && property.Name is nameof(AED.Created) or nameof(AED.LastUpdated))
					&& !values.ContainsKey(property.Name)) {
					throw new CsvImportException($"rows[{row.Number}].{table}.{property.Name}",
						$"Column {table}.{property.Name} is required to create a new record.");
				}
			}
			database.Add(entity);
		}
		foreach ((String column, Object? value) in values) {
			entry.Property(column).CurrentValue = value;
		}
		if (entity is AED aed) {
			if (aed.Latitude is < -90 or > 90) {
				throw new CsvImportException($"rows[{row.Number}].AEDs.Latitude", "Latitude must be between -90 and 90 degrees.");
			}
			if (aed.Longitude is < -180 or > 180) {
				throw new CsvImportException($"rows[{row.Number}].AEDs.Longitude", "Longitude must be between -180 and 180 degrees.");
			}
			if (aed.AvailabilityStartHour is < 0 or > 23 || aed.AvailabilityEndHour is < 0 or > 24
				|| (aed.AvailabilityStartHour is not null && aed.AvailabilityStartHour == aed.AvailabilityEndHour)) {
				throw new CsvImportException($"rows[{row.Number}].AEDs",
					"Known availability hours must be in the 0-23 / 0-24 ranges and unequal when both are supplied.");
			}
			database.ChangeTracker.DetectChanges();
			if (!inserted && entry.State == EntityState.Modified && !values.ContainsKey(nameof(AED.LastUpdated))) {
				aed.LastUpdated = DateTime.UtcNow;
			}
		}
		database.ChangeTracker.DetectChanges();
		Boolean updated = !inserted && entry.State == EntityState.Modified;
		await database.SaveChangesAsync(cancellationToken);
		CsvImportTableResult count = counts[table];
		counts[table] = new CsvImportTableResult(count.Inserted + (inserted ? 1 : 0), count.Updated + (updated ? 1 : 0));
		return entity;
	}

	private sealed record ColumnMapping(Int32 Index, String Table, IProperty Property, VariableType FromType, VariableType ToType);
	private sealed record ImportRow(Int32 Number, Dictionary<String, Dictionary<String, Object?>> Values);
}