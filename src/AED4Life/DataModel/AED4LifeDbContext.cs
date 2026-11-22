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
