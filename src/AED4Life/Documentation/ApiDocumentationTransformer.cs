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
							new AEDOwnerResponse("001234567", true, "Example school", "Warszawa", "01-357", "Example Street")
						}),
						["empty"] = Example("No owners exist", Array.Empty<AEDOwnerResponse>())
					};
				break;

			case "CreateTranslationProfile":
				Transporter transporter = new() {
					TransporterUnits = [
						new TransporterUnit {
							FromColumn = "owner_name", FromType = VariableType.STRING,
							ToColumn = "Name", ToType = VariableType.STRING
						},
						new TransporterUnit {
							FromColumn = "regon", FromType = VariableType.STRING,
							ToColumn = "RegonNumber", ToType = VariableType.STRING
						}
					]
				};
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
						["created"] = Example("Created translation profile", new TranslationProfileResponse(1, "Owner import", transporter))
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
