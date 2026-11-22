using AED4Life.DataModel;
using AED4Life.DataModel.Entities;
using AED4Life.Documentation;
using AED4Life.Endpoints;
using AED4Life.Storage;
using AED4Life.Translation;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.OpenApi;
using Scalar.AspNetCore;

WebApplicationBuilder builder = WebApplication.CreateBuilder(args);

String? connectionString = builder.Configuration.GetConnectionString("AED4Life");
if (String.IsNullOrWhiteSpace(connectionString)) {
	throw new InvalidOperationException(
		"Configure ConnectionStrings:AED4Life using user secrets or the ConnectionStrings__AED4Life environment variable.");
}

builder.Services.AddDbContext<AED4LifeDbContext>(options =>
	options.UseMySql(connectionString, new MariaDbServerVersion(new Version(12, 3, 3))));
builder.Services.AddScoped<TranslationEngine>();
builder.Services.AddSingleton<ReportImageStorage>();
builder.Services.Configure<PasswordHasherOptions>(options => options.IterationCount = 210_000);
builder.Services.AddScoped<IPasswordHasher<User>, PasswordHasher<User>>();

// Add services to the container.
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi(options => {
	options.AddDocumentTransformer((document, context, cancellationToken) => {
		document.Info = new OpenApiInfo {
			Title = "AED4Life API",
			Version = "v1",
			Description = "AED lookup, reports with image uploads, reusable translation profiles, and transactional CSV import. Includes a sample weather endpoint."
		};
		return Task.CompletedTask;
	});
	options.AddOperationTransformer<ApiDocumentationTransformer>();
});

WebApplication app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment()) {
	app.MapOpenApi();
	app.MapScalarApiReference(options => options.WithTitle("AED4Life API"));
}

app.UseHttpsRedirection();

app.MapAedEndpoints();
app.MapTranslationEndpoints();
app.MapReportEndpoints();

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
	.WithName("GetWeatherForecast")
	.WithTags("Weather")
	.WithSummary("Get sample weather forecasts")
	.WithDescription("Returns five randomly generated daily forecasts with Celsius and calculated Fahrenheit temperatures. "
		+ "This demonstration endpoint does not access the database. No request body is required.");

app.Run();

record WeatherForecast(DateOnly Date, Int32 TemperatureC, String? Summary) {
	public Int32 TemperatureF => 32 + (Int32)(TemperatureC / 0.5556);
}