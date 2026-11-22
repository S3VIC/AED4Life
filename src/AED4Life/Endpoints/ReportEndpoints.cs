using System.Text.Json;
using AED4Life.DataModel;
using AED4Life.DataModel.DTOs;
using AED4Life.DataModel.Entities;
using AED4Life.DataModel.Enums;
using AED4Life.Requests;
using AED4Life.Storage;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using MySqlConnector;

namespace AED4Life.Endpoints;

public static class ReportEndpoints {
	private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

	public static RouteGroupBuilder MapReportEndpoints(this IEndpointRouteBuilder endpoints) {
		RouteGroupBuilder group = endpoints.MapGroup("/api/zgloszenia").WithTags("Zgloszenia");
		group.MapPost("", CreateAsync)
			.WithName("CreateAEDReport")
			.WithSummary("Create an AED report with an optional image")
			.WithDescription("Send multipart/form-data with a metadata JSON string containing userId, a required nonblank device-placement description, optional aedId, and photoUrl when no image is uploaded. "
				+ "Optional availabilityStartHour (0-23) and availabilityEndHour (0-24) support overnight ranges and may be supplied independently; if both are supplied, they must differ. "
				+ "Use 0-24 for all-day availability. Optional isPubliclyAccessible is true/false, or null when unknown. "
				+ "Optional rating must be an integer from 0 to 100 inclusive; omit it or use null when unknown. "
				+ "Alternatively upload a nonempty PNG/JPEG in image (maximum 5 MiB); do not provide both an image and a nonblank photoUrl. "
				+ "File signatures are checked and original filenames are ignored. Uploaded images are stored outside the database; photoUrl then contains a generated filename relative to ReportImages:Directory. "
				+ "External photoUrl values are not fetched or checked for file contents. The server sets Created/LastUpdated to UTC and Status to Submitted. "
				+ "User IDs are accepted without authentication for this prototype; this does not verify the caller's identity.")
			.DisableAntiforgery()
			.WithMetadata(new RequestSizeLimitAttribute(ReportImageStorage.MaxImageBytes + 128 * 1024))
			.ProducesProblem(StatusCodes.Status409Conflict)
			.ProducesProblem(StatusCodes.Status413PayloadTooLarge)
			.ProducesProblem(StatusCodes.Status415UnsupportedMediaType)
			.ProducesProblem(StatusCodes.Status503ServiceUnavailable);
		return group;
	}

	private static async Task<Results<Created<AEDReportResponse>, ValidationProblem, ProblemHttpResult>> CreateAsync(
		[FromForm] String metadata, IFormFile? image, AED4LifeDbContext database,
		ReportImageStorage storage, ILoggerFactory loggerFactory, CancellationToken cancellationToken) {
		if (String.IsNullOrWhiteSpace(metadata) || metadata.Length > 16 * 1024) {
			return TypedResults.ValidationProblem(new Dictionary<String, String[]> {
				["metadata"] = ["Provide a JSON metadata object of at most 16384 characters."]
			});
		}
		CreateAEDReportRequest? request;
		try {
			request = JsonSerializer.Deserialize<CreateAEDReportRequest>(metadata, JsonOptions);
		} catch (JsonException) {
			return TypedResults.ValidationProblem(new Dictionary<String, String[]> {
				["metadata"] = ["Metadata must be a JSON object containing only userId, aedId, photoUrl, description, availabilityStartHour, availabilityEndHour, isPubliclyAccessible, and rating, with valid field types."]
			});
		}
		if (request is null) {
			return TypedResults.ValidationProblem(new Dictionary<String, String[]> { ["metadata"] = ["Metadata cannot be null."] });
		}

		Dictionary<String, String[]> errors = [];
		String? description = request.Description?.Trim();
		if (String.IsNullOrWhiteSpace(description)) {
			errors["description"] = ["A nonblank description of the device placement is required."];
		}
		if (request.Rating is < 0 or > 100) {
			errors["rating"] = ["Rating must be an integer between 0 and 100."];
		}
		if (request.AvailabilityStartHour is < 0 or > 23) {
			errors["availabilityStartHour"] = ["The opening hour must be between 0 and 23."];
		}
		if (request.AvailabilityEndHour is < 0 or > 24) {
			errors["availabilityEndHour"] = ["The closing hour must be between 0 and 24."];
		}
		if (request.AvailabilityStartHour is not null && request.AvailabilityStartHour == request.AvailabilityEndHour) {
			errors["availabilityEndHour"] = ["Opening and closing hours must differ. Use 0 and 24 for all-day availability."];
		}
		if (request.UserId is null or <= 0) {
			errors["userId"] = ["A positive userId is required."];
		}
		if (request.AEDId is <= 0) {
			errors["aedId"] = ["When supplied, aedId must be positive."];
		}
		String? photoUrl = request.PhotoUrl?.Trim();
		if (image is null && String.IsNullOrWhiteSpace(photoUrl)) {
			errors["photoUrl"] = ["Provide a nonblank photoUrl when no image is uploaded."];
		} else if (image is not null && !String.IsNullOrWhiteSpace(photoUrl)) {
			errors["image"] = ["Provide either an image or photoUrl, not both."];
		}
		if (errors.Count > 0) {
			return TypedResults.ValidationProblem(errors);
		}
		if (!await database.Users.AnyAsync(user => user.Id == request.UserId, cancellationToken)) {
			errors["userId"] = ["The specified user does not exist."];
		}
		if (request.AEDId is Int64 aedId && !await database.AEDs.AnyAsync(aed => aed.Id == aedId, cancellationToken)) {
			errors["aedId"] = ["The specified AED does not exist."];
		}
		if (errors.Count > 0) {
			return TypedResults.ValidationProblem(errors);
		}

		String? storedImage = null;
		Boolean persisted = false;
		try {
			if (image is not null) {
				storedImage = await storage.SaveAsync(image, cancellationToken);
				photoUrl = storedImage;
			}
			DateTime now = DateTime.UtcNow;
			AEDReport report = new() {
				UserId = request.UserId!.Value,
				AEDId = request.AEDId,
				PhotoUrl = photoUrl!,
				Description = description!,
				AvailabilityStartHour = request.AvailabilityStartHour,
				AvailabilityEndHour = request.AvailabilityEndHour,
				IsPubliclyAccessible = request.IsPubliclyAccessible,
				Rating = request.Rating,
				Created = now,
				LastUpdated = now,
				Status = ReportStatus.Submitted
			};
			database.AEDReports.Add(report);
			await database.SaveChangesAsync(cancellationToken);
			persisted = true;
			return TypedResults.Created(String.Empty, new AEDReportResponse(
				report.Id, report.UserId, report.AEDId, report.PhotoUrl,
				report.Description, report.AvailabilityStartHour, report.AvailabilityEndHour, report.IsPubliclyAccessible, report.Rating,
				now, now, report.Status));
		} catch (ReportImageValidationException exception) {
			if (exception.StatusCode == StatusCodes.Status400BadRequest) {
				return TypedResults.ValidationProblem(new Dictionary<String, String[]> { ["image"] = [exception.Message] });
			}
			return TypedResults.Problem(statusCode: exception.StatusCode, title: exception.Message);
		} catch (DbUpdateException exception) when (exception.InnerException is MySqlException { Number: 1451 or 1452 or 1048 or 1364 or 1406 or 4025 }) {
			return TypedResults.Problem(statusCode: StatusCodes.Status409Conflict,
				title: "The report conflicts with database constraints. No report was created.");
		} catch (Exception exception) when (exception is IOException or UnauthorizedAccessException) {
			loggerFactory.CreateLogger("ReportEndpoints").LogError(exception, "Report image storage failed.");
			return TypedResults.Problem(statusCode: StatusCodes.Status503ServiceUnavailable,
				title: "Image storage is unavailable. No report was created.");
		} finally {
			if (!persisted && storedImage is not null) {
				storage.Delete(storedImage);
			}
		}
	}
}
