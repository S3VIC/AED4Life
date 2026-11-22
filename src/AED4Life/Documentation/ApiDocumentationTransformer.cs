using System.Text.Json;
using AED4Life.DataModel.DTOs;
using AED4Life.Requests;
using AED4Life.Trananslation;
using Microsoft.AspNetCore.OpenApi;
using Microsoft.OpenApi;

namespace AED4Life.Documentation;

public sealed class ApiDocumentationTransformer : IOpenApiOperationTransformer {
	private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

	public Task TransformAsync(OpenApiOperation operation, OpenApiOperationTransformerContext context,
		CancellationToken cancellationToken) {
		switch (operation.OperationId) {
			case "GetAEDOwners":
				ResponseContent(operation, "200", "All owners with their city and street details; an empty array when none exist.")
					.Examples = new Dictionary<String, IOpenApiExample> {
						["owners"] = Example("Owners with joined address details", new[] {
							new AEDOwnerResponse("001234567", true, "Example school", "Warszawa", "Example Street")
						}),
						["unknownLocation"] = Example("Owner with unknown REGON, public flag, and location", new[] {
							new AEDOwnerResponse(null, null, "Example operator", null, null)
						}),
						["empty"] = Example("No owners exist", Array.Empty<AEDOwnerResponse>())
					};
				break;

			case "GetTranslationProfiles":
			case "GetTranslationProfileByName":
			case "CreateTranslationProfile":
				Transporter transporter = new() {
					TransporterUnits = [
						new TransporterUnit {
							FromColumn = "owner_name", FromType = VariableType.STRING,
							ToColumn = "AEDOwners.Name", ToType = VariableType.STRING
						},
						new TransporterUnit {
							FromColumn = "regon", FromType = VariableType.STRING,
							ToColumn = "AEDOwners.RegonNumber", ToType = VariableType.STRING
						},
						new TransporterUnit {
							FromColumn = "is_public", FromType = VariableType.BOOLEAN,
							ToColumn = "AEDOwners.IsPublic", ToType = VariableType.BOOLEAN
						},
						new TransporterUnit {
							FromColumn = "city_id", FromType = VariableType.INTEGER,
							ToColumn = "AEDOwners.CityId", ToType = VariableType.INTEGER
						},
						new TransporterUnit {
							FromColumn = "street_id", FromType = VariableType.INTEGER,
							ToColumn = "AEDOwners.StreetId", ToType = VariableType.INTEGER
						}
					]
				};
				TranslationProfileResponse profile = new(1, "Owner import", transporter);
				if (operation.OperationId == "GetTranslationProfiles") {
					ResponseContent(operation, "200", "All profiles ordered by name, with mapping units in stored position order.")
						.Examples = new Dictionary<String, IOpenApiExample> {
							["profiles"] = Example("Saved translation profiles", new[] { profile }),
							["empty"] = Example("No profiles exist", Array.Empty<TranslationProfileResponse>())
						};
					break;
				}
				if (operation.OperationId == "GetTranslationProfileByName") {
					ResponseContent(operation, "200", "The matching profile with mapping units in stored position order.")
						.Examples = new Dictionary<String, IOpenApiExample> {
							["profile"] = Example("Saved translation profile", profile)
						};
					ResponseContent(operation, "404", "No profile matches the supplied name.", "application/problem+json")
						.Examples = new Dictionary<String, IOpenApiExample> {
							["notFound"] = Example("Profile not found", TypedResults.Problem(
								statusCode: StatusCodes.Status404NotFound,
								title: "A translation profile with this name does not exist.").ProblemDetails)
						};
					break;
				}
				if (operation.RequestBody is not OpenApiRequestBody requestBody
					|| requestBody.Content is null
					|| !requestBody.Content.TryGetValue("application/json", out OpenApiMediaType? requestContent)) {
					throw new InvalidOperationException("The translation profile endpoint must declare a JSON request body.");
				}
				requestBody.Description = "A unique profile name and an ordered array of source-to-destination mappings.";
				requestContent.Examples = new Dictionary<String, IOpenApiExample> {
					["ownerImport"] = Example("Map imported owner columns", new CreateTranslationConfig("Owner import", transporter))
				};
				ResponseContent(operation, "201", "Profile and all mapping units were created atomically.")
					.Examples = new Dictionary<String, IOpenApiExample> {
						["created"] = Example("Created translation profile", profile)
					};
				ResponseContent(operation, "400", "Invalid profile fields. Malformed JSON also returns HTTP 400.", "application/problem+json")
					.Examples = new Dictionary<String, IOpenApiExample> {
						["validation"] = Example("Missing name and empty mapping array", TypedResults.ValidationProblem(
							new Dictionary<String, String[]> {
								["name"] = ["A profile name between 1 and 255 characters is required."],
								["transporter.transporterUnits"] = ["At least one mapping unit is required."]
							}).ProblemDetails)
					};
				ResponseContent(operation, "409", "A profile with the same name already exists.", "application/problem+json")
					.Examples = new Dictionary<String, IOpenApiExample> {
						["duplicateName"] = Example("Duplicate profile name", TypedResults.Problem(
							statusCode: StatusCodes.Status409Conflict,
							title: "A translation profile with this name already exists.").ProblemDetails)
					};
				break;

			case "ImportTranslationCsv":
				if (operation.RequestBody is not OpenApiRequestBody importBody) {
					throw new InvalidOperationException("The CSV import endpoint must declare a multipart request body.");
				}
				importBody.Description = "A multipart/form-data upload with one CSV file in the file field. "
					+ "Use UTF-8, a header record, comma delimiters, and standard CSV quoting. "
					+ "Profile destinations must use Cities.Name, Streets.Name, PostalCodes.Code, Addresses.BuildingNumber, "
					+ "AEDOwners.RegonNumber, AEDs.SerialNumber, or other writable columns of those tables. "
					+ "IDs are generated; mapped related records supply foreign keys automatically, and partial addresses are inferred for AEDs. "
					+ "Matching keys: city/street name, postal code, address location and building number, owner REGON, AED serial number. "
					+ "Without REGON, owners match by name + city + street; without serial numbers, AEDs match by latitude + longitude + address "
					+ "when both coordinates are known, or are inserted otherwise. "
					+ "Business values are nullable; empty lookups/owners are skipped and existing records retain unmapped values. "
					+ "Numbers use invariant culture; booleans accept true/false or 1/0. "
					+ "Empty/whitespace cells and literal NULL or \\N become SQL NULL. Invalid nonempty values are rejected.";
				ResponseContent(operation, "200", "The entire file was committed. Counts report insert/update operations per table.")
					.Examples = new Dictionary<String, IOpenApiExample> {
						["imported"] = Example("Imported one AED and its related address", new CsvImportResponse(
							"AED import", 1, new Dictionary<String, CsvImportTableResult> {
								["Cities"] = new(1, 0), ["Streets"] = new(1, 0), ["PostalCodes"] = new(1, 0),
								["Addresses"] = new(1, 0), ["AEDs"] = new(1, 0)
							}))
					};
				ResponseContent(operation, "400", "Invalid CSV, profile mappings, missing values, or ambiguous matching keys. The file was rolled back.", "application/problem+json")
					.Examples = new Dictionary<String, IOpenApiExample> {
						["invalidValue"] = Example("Invalid building number", TypedResults.ValidationProblem(
							new Dictionary<String, String[]> {
								["rows[2].Addresses.BuildingNumber"] = ["The value cannot be converted to an integer building number."]
							}).ProblemDetails)
					};
				ResponseContent(operation, "404", "No profile matches the supplied name.", "application/problem+json")
					.Examples = new Dictionary<String, IOpenApiExample> {
						["notFound"] = Example("Profile not found", TypedResults.Problem(
							statusCode: StatusCodes.Status404NotFound,
							title: "A translation profile with this name does not exist.").ProblemDetails)
					};
				ResponseContent(operation, "409", "A database constraint or concurrent operation prevented the import. The file was rolled back.", "application/problem+json")
					.Examples = new Dictionary<String, IOpenApiExample> {
						["conflict"] = Example("Database conflict", TypedResults.Problem(
							statusCode: StatusCodes.Status409Conflict,
							title: "The import conflicts with database constraints. No rows were imported.").ProblemDetails)
					};
				ResponseContent(operation, "415", "The uploaded file must have a .csv filename.", "application/problem+json")
					.Examples = new Dictionary<String, IOpenApiExample> {
						["unsupportedFile"] = Example("CSV files only", TypedResults.Problem(
							statusCode: StatusCodes.Status415UnsupportedMediaType,
							title: "Only CSV files are supported.").ProblemDetails)
					};
				break;

			case "GetWeatherForecast":
				ResponseContent(operation, "200", "Five randomly generated daily forecasts; this is demonstration data.")
					.Examples = new Dictionary<String, IOpenApiExample> {
						["forecasts"] = Example("Five sample forecasts", new[] {
							new WeatherForecast(new DateOnly(2026, 11, 22), 10, "Cool"),
							new WeatherForecast(new DateOnly(2026, 11, 23), 0, "Chilly"),
							new WeatherForecast(new DateOnly(2026, 11, 24), 20, "Mild"),
							new WeatherForecast(new DateOnly(2026, 11, 25), -5, "Freezing"),
							new WeatherForecast(new DateOnly(2026, 11, 26), 25, "Warm")
						})
					};
				break;
		}

		return Task.CompletedTask;
	}

	private static OpenApiExample Example<T>(String summary, T value) => new() {
		Summary = summary,
		Value = JsonSerializer.SerializeToNode(value, JsonOptions)
	};

	private static OpenApiMediaType ResponseContent(OpenApiOperation operation, String status,
		String description, String contentType = "application/json") {
		if (operation.Responses is null
			|| !operation.Responses.TryGetValue(status, out IOpenApiResponse? response)
			|| response is not OpenApiResponse documentedResponse
			|| documentedResponse.Content is null
			|| !documentedResponse.Content.TryGetValue(contentType, out OpenApiMediaType? content)) {
			throw new InvalidOperationException($"Endpoint '{operation.OperationId}' must declare a {status} {contentType} response.");
		}
		documentedResponse.Description = description;
		return content;
	}
}
