using AED4Life.DataModel.Entities;
using Microsoft.EntityFrameworkCore;

namespace AED4Life.DataModel;

public sealed class AED4LifeDbContext(DbContextOptions<AED4LifeDbContext> options) : DbContext(options) {
	public DbSet<AED> AEDs => Set<AED>();
	public DbSet<AEDOwner> AEDOwners => Set<AEDOwner>();
	public DbSet<City> Cities => Set<City>();
	public DbSet<Street> Streets => Set<Street>();
	public DbSet<Address> Addresses => Set<Address>();
	public DbSet<PostalCode> PostalCodes => Set<PostalCode>();
	public DbSet<User> Users => Set<User>();
	public DbSet<AEDReport> AEDReports => Set<AEDReport>();
	public DbSet<TranslationProfile> TranslationProfiles => Set<TranslationProfile>();
	public DbSet<TranslationProfileUnit> TranslationProfileUnits => Set<TranslationProfileUnit>();

	protected override void OnModelCreating(ModelBuilder modelBuilder) {
		modelBuilder.HasCharSet("utf8mb4").UseCollation("utf8mb4_unicode_ci");

		modelBuilder.Entity<City>(entity => {
			entity.ToTable("Cities");
			entity.HasKey(city => city.Id);
			entity.Property(city => city.Id).ValueGeneratedOnAdd();
		});

		modelBuilder.Entity<Street>(entity => {
			entity.ToTable("Streets");
			entity.HasKey(street => street.Id);
			entity.Property(street => street.Id).ValueGeneratedOnAdd();
		});

		modelBuilder.Entity<PostalCode>(entity => {
			entity.ToTable("PostalCodes");
			entity.HasKey(postalCode => postalCode.Id);
			entity.Property(postalCode => postalCode.Id).ValueGeneratedOnAdd();
			entity.Property(postalCode => postalCode.Code).HasMaxLength(6);
		});

		modelBuilder.Entity<Address>(entity => {
			entity.ToTable("Addresses");
			entity.HasKey(address => address.Id);
			entity.Property(address => address.Id).ValueGeneratedOnAdd();
			entity.HasOne<City>().WithMany().HasForeignKey(address => address.CityId)
				.OnDelete(DeleteBehavior.Restrict)
				.HasConstraintName("FK_Address_Cities_CityId");
			entity.HasOne<Street>().WithMany().HasForeignKey(address => address.StreetId)
				.OnDelete(DeleteBehavior.Restrict)
				.HasConstraintName("FK_Address_Streets_StreetId");
			entity.HasOne<PostalCode>().WithMany().HasForeignKey(address => address.PostalCodeId)
				.OnDelete(DeleteBehavior.Restrict)
				.HasConstraintName("FK_Address_PostalCodes_PostalCodeId");
		});

		modelBuilder.Entity<AED>(entity => {
			entity.ToTable("AEDs", table => {
				table.HasCheckConstraint("CK_AEDs_Access", "`Access` IS NULL OR `Access` IN (0, 1, 2)");
				table.HasCheckConstraint("CK_AEDs_Rating", "`Rating` IS NULL OR `Rating` IN (0, 1)");
				table.HasCheckConstraint("CK_AEDs_Latitude", "`Latitude` IS NULL OR `Latitude` BETWEEN -90 AND 90");
				table.HasCheckConstraint("CK_AEDs_Longitude", "`Longitude` IS NULL OR `Longitude` BETWEEN -180 AND 180");
				table.HasCheckConstraint("CK_AEDs_AvailabilityHours",
					"(`AvailabilityStartHour` IS NULL OR `AvailabilityStartHour` BETWEEN 0 AND 23) "
					+ "AND (`AvailabilityEndHour` IS NULL OR `AvailabilityEndHour` BETWEEN 0 AND 24) "
					+ "AND (`AvailabilityStartHour` IS NULL OR `AvailabilityEndHour` IS NULL "
					+ "OR `AvailabilityStartHour` <> `AvailabilityEndHour`)");
			});
			entity.HasKey(aed => aed.Id);
			entity.Property(aed => aed.Id).ValueGeneratedOnAdd();
			entity.Property(aed => aed.Created).HasColumnType("datetime(6)");
			entity.Property(aed => aed.LastUpdated).HasColumnType("datetime(6)");
			entity.Property(aed => aed.Latitude).HasColumnType("double");
			entity.Property(aed => aed.Longitude).HasColumnType("double");
			entity.Property(aed => aed.Access).HasConversion<Int32>();
			entity.Property(aed => aed.Rating).HasConversion<Int32>();
			entity.HasOne<Address>().WithMany().HasForeignKey(aed => aed.AddressId)
				.OnDelete(DeleteBehavior.Restrict)
				.HasConstraintName("FK_AEDs_Address_AddressId");
			entity.HasOne<AEDOwner>().WithMany().HasForeignKey(aed => aed.OwnerId)
				.OnDelete(DeleteBehavior.Restrict);
		});

		modelBuilder.Entity<AEDOwner>(entity => {
			entity.ToTable("AEDOwners");
			entity.HasKey(owner => owner.Id);
			entity.Property(owner => owner.Id).ValueGeneratedOnAdd();
			entity.Property(owner => owner.RegonNumber).HasMaxLength(14);
			entity.HasIndex(owner => owner.RegonNumber).IsUnique();
			entity.HasOne<City>().WithMany().HasForeignKey(owner => owner.CityId)
				.OnDelete(DeleteBehavior.Restrict);
			entity.HasOne<Street>().WithMany().HasForeignKey(owner => owner.StreetId)
				.OnDelete(DeleteBehavior.Restrict);
		});

		modelBuilder.Entity<User>(entity => {
			entity.ToTable("Users", table => {
				table.HasCheckConstraint("CK_Users_Type", "`Type` IN (0, 1, 2, 3)");
				table.HasCheckConstraint("CK_Users_PasswordHash", "CHAR_LENGTH(TRIM(`PasswordHash`)) > 0");
			});
			entity.HasKey(user => user.Id);
			entity.Property(user => user.Id).ValueGeneratedOnAdd();
			entity.Property(user => user.Username).HasMaxLength(255);
			entity.Property(user => user.PasswordHash).HasMaxLength(512);
			entity.HasIndex(user => user.Username).IsUnique();
			entity.Property(user => user.BirthDate).HasColumnType("date");
			entity.Property(user => user.Type).HasConversion<Int32>();
			entity.HasOne<Address>().WithMany().HasForeignKey(user => user.AddressId)
				.OnDelete(DeleteBehavior.Restrict);
		});

		modelBuilder.Entity<AEDReport>(entity => {
			entity.ToTable("AEDReports", table => {
				table.HasCheckConstraint("CK_AEDReports_Status", "`Status` IN (0, 1, 2, 3)");
				table.HasCheckConstraint("CK_AEDReports_PhotoUrl", "`PhotoUrl` REGEXP '[^[:space:]]'");
				table.HasCheckConstraint("CK_AEDReports_Description", "`Description` REGEXP '[^[:space:]]'");
				table.HasCheckConstraint("CK_AEDReports_IsPubliclyAccessible", "`IsPubliclyAccessible` IS NULL OR `IsPubliclyAccessible` IN (0, 1)");
				table.HasCheckConstraint("CK_AEDReports_Rating", "`Rating` IS NULL OR `Rating` BETWEEN 0 AND 100");
				table.HasCheckConstraint("CK_AEDReports_AvailabilityHours",
					"(`AvailabilityStartHour` IS NULL OR `AvailabilityStartHour` BETWEEN 0 AND 23) "
					+ "AND (`AvailabilityEndHour` IS NULL OR `AvailabilityEndHour` BETWEEN 0 AND 24) "
					+ "AND (`AvailabilityStartHour` IS NULL OR `AvailabilityEndHour` IS NULL "
					+ "OR `AvailabilityStartHour` <> `AvailabilityEndHour`)");
			});
			entity.HasKey(report => report.Id);
			entity.Property(report => report.Id).ValueGeneratedOnAdd();
			entity.Property(report => report.Created).HasColumnType("datetime(6)");
			entity.Property(report => report.LastUpdated).HasColumnType("datetime(6)");
			entity.Property(report => report.Status).HasConversion<Int32>();
			entity.HasOne<User>().WithMany().HasForeignKey(report => report.UserId)
				.OnDelete(DeleteBehavior.Restrict);
			entity.HasOne<AED>().WithMany().HasForeignKey(report => report.AEDId)
				.OnDelete(DeleteBehavior.Restrict);
		});

		modelBuilder.Entity<TranslationProfile>(entity => {
			entity.ToTable("TranslationProfiles");
			entity.HasKey(profile => profile.Id);
			entity.Property(profile => profile.Id).ValueGeneratedOnAdd();
			entity.Property(profile => profile.Name).HasMaxLength(255);
			entity.HasIndex(profile => profile.Name).IsUnique();
			entity.HasMany(profile => profile.Units).WithOne()
				.HasForeignKey(unit => unit.TranslationProfileId)
				.OnDelete(DeleteBehavior.Cascade)
				.HasConstraintName("FK_TranslationProfileUnits_Profile");
		});

		modelBuilder.Entity<TranslationProfileUnit>(entity => {
			entity.ToTable("TranslationProfileUnits", table => {
				table.HasCheckConstraint("CK_TranslationProfileUnits_Position", "`Position` >= 0");
				table.HasCheckConstraint("CK_TranslationProfileUnits_FromType", "`FromType` IN (0, 1, 2, 3)");
				table.HasCheckConstraint("CK_TranslationProfileUnits_ToType", "`ToType` IN (0, 1, 2, 3)");
			});
			entity.HasKey(unit => unit.Id);
			entity.Property(unit => unit.Id).ValueGeneratedOnAdd();
			entity.Property(unit => unit.FromType).HasConversion<Int32>();
			entity.Property(unit => unit.ToType).HasConversion<Int32>();
			entity.HasIndex(unit => new { unit.TranslationProfileId, unit.Position }).IsUnique();
		});
	}
}
