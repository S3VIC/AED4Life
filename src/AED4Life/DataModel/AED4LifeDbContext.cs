using AED4Life.DataModel.Entities;
using Microsoft.EntityFrameworkCore;

namespace AED4Life.DataModel;

public sealed class AED4LifeDbContext(DbContextOptions<AED4LifeDbContext> options) : DbContext(options) {
	public DbSet<AED> AEDs => Set<AED>();
	public DbSet<AEDOwner> AEDOwners => Set<AEDOwner>();
	public DbSet<City> Cities => Set<City>();
	public DbSet<Street> Streets => Set<Street>();

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

		modelBuilder.Entity<AED>(entity => {
			entity.ToTable("AEDs");
			entity.HasKey(aed => aed.Id);
			entity.Property(aed => aed.Id).ValueGeneratedOnAdd();
			entity.Property(aed => aed.Created).HasColumnType("datetime(6)");
			entity.Property(aed => aed.LastUpdated).HasColumnType("datetime(6)");
			entity.HasOne<City>().WithMany().HasForeignKey(aed => aed.CityId)
				.OnDelete(DeleteBehavior.Restrict);
			entity.HasOne<Street>().WithMany().HasForeignKey(aed => aed.StreetId)
				.OnDelete(DeleteBehavior.Restrict);
		});

		modelBuilder.Entity<AEDOwner>(entity => {
			entity.ToTable("AEDOwners");
			entity.HasKey(owner => owner.RegonNumber);
			entity.Property(owner => owner.RegonNumber).ValueGeneratedNever();
			entity.HasOne<City>().WithMany().HasForeignKey(owner => owner.CityId)
				.OnDelete(DeleteBehavior.Restrict);
			entity.HasOne<Street>().WithMany().HasForeignKey(owner => owner.StreetId)
				.OnDelete(DeleteBehavior.Restrict);
		});
	}
}
