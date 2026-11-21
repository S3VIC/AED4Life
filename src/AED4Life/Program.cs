using AED4Life.DataModel;
using AED4Life.Endpoints;
using Microsoft.EntityFrameworkCore;

WebApplicationBuilder builder = WebApplication.CreateBuilder(args);

String? connectionString = builder.Configuration.GetConnectionString("AED4Life");
if (String.IsNullOrWhiteSpace(connectionString)) {
	throw new InvalidOperationException(
		"Configure ConnectionStrings:AED4Life using user secrets or the ConnectionStrings__AED4Life environment variable.");
}

builder.Services.AddDbContext<AED4LifeDbContext>(options =>
	options.UseMySql(connectionString, new MariaDbServerVersion(new Version(12, 3, 3))));

// Add services to the container.
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

WebApplication app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment()) {
	app.MapOpenApi();
}

app.UseHttpsRedirection();

app.MapAEDEndpoints();

String[] summaries = new[] {
	"Freezing", "Bracing", "Chilly", "Cool", "Mild", "Warm", "Balmy", "Hot", "Sweltering", "Scorching"
};

app.MapGet("/weatherforecast", () => {
		WeatherForecast[] forecast = [
			.. Enumerable.Range(1, 5).Select(index =>
				new WeatherForecast
				(
					DateOnly.FromDateTime(DateTime.Now.AddDays(index)),
					Random.Shared.Next(-20, 55),
					summaries[Random.Shared.Next(summaries.Length)]
				))
		];
		return forecast;
	})
	.WithName("GetWeatherForecast");

app.Run();

record WeatherForecast(DateOnly Date, Int32 TemperatureC, String? Summary) {
	public Int32 TemperatureF => 32 + (Int32)(TemperatureC / 0.5556);
}