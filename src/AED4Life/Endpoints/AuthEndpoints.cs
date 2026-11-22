using System.Security.Claims;
using AED4Life.DataModel;
using AED4Life.DataModel.DTOs;
using AED4Life.DataModel.Entities;
using AED4Life.DataModel.Enums;
using AED4Life.Requests;
using Microsoft.AspNetCore.Authentication.BearerToken;
using Microsoft.AspNetCore.Http.HttpResults;
using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;

namespace AED4Life.Endpoints;

public static class AuthEndpoints {
	public const String LoginRateLimitPolicy = "login";

	private static readonly User DummyUser = new() { Username = "-", FirstName = "-", LastName = "-" };
	// Verified for unknown usernames so that response time does not reveal whether an account exists.
	private static readonly String DummyHash = new PasswordHasher<User>(
		Options.Create(new PasswordHasherOptions { IterationCount = 210_000 }))
		.HashPassword(DummyUser, Guid.NewGuid().ToString("N"));

	public static IEndpointRouteBuilder MapAuthEndpoints(this IEndpointRouteBuilder endpoints) {
		endpoints.MapPost("/api/login", LoginAsync)
			.WithName("Login")
			.WithTags("Authentication")
			.WithSummary("Log in with a username and password")
			.WithDescription("Send a JSON body with username and password. The password is verified against the stored Identity V3 PBKDF2 hash; "
				+ "plaintext passwords are never stored or logged. On success the response is a bearer token "
				+ "({\"tokenType\":\"Bearer\",\"accessToken\":\"...\",\"expiresIn\":28800,\"refreshToken\":\"...\"}); send it as 'Authorization: Bearer <accessToken>'. "
				+ "Unknown users and wrong passwords return the same 401 response. Requests are rate limited per client address (429).")
			.RequireRateLimiting(LoginRateLimitPolicy)
			.ProducesProblem(StatusCodes.Status401Unauthorized)
			.ProducesProblem(StatusCodes.Status429TooManyRequests);

		endpoints.MapGet("/api/me", GetCurrentUserAsync)
			.WithName("GetCurrentUser")
			.WithTags("Authentication")
			.WithSummary("Get the logged-in user")
			.WithDescription("Requires a bearer token. Returns the user's id, username, name and type. The type is read from the database on every call, "
				+ "so a promotion is visible immediately.")
			.RequireAuthorization()
			.ProducesProblem(StatusCodes.Status401Unauthorized);

		RouteGroupBuilder users = endpoints.MapGroup("/api/users").WithTags("Users").RequireAuthorization();
		users.MapGet("", GetUsersAsync)
			.WithName("GetUsers")
			.WithSummary("List users (administrators only)")
			.WithDescription("Requires an administrator bearer token. Returns every user ordered by username, without password hashes.")
			.ProducesProblem(StatusCodes.Status401Unauthorized)
			.ProducesProblem(StatusCodes.Status403Forbidden);
		users.MapPost("/{id:long}/promote", PromoteAsync)
			.WithName("PromoteUserToMaintainer")
			.WithSummary("Promote a user to maintainer (administrators only)")
			.WithDescription("Requires an administrator bearer token. Changes a Normal or PublicRepresentative user to Maintainer. "
				+ "A user who is already a Maintainer is returned unchanged; administrators cannot be changed (409). "
				+ "Maintainers can accept or reject AED reports. The promoted user sees the new role immediately in /api/me.")
			.ProducesProblem(StatusCodes.Status401Unauthorized)
			.ProducesProblem(StatusCodes.Status403Forbidden)
			.ProducesProblem(StatusCodes.Status404NotFound)
			.ProducesProblem(StatusCodes.Status409Conflict);
		return endpoints;
	}

	/// <summary>Loads the caller from the database (not from token claims) so role changes apply immediately.</summary>
	internal static async Task<User?> GetCallerAsync(ClaimsPrincipal principal, AED4LifeDbContext database, CancellationToken cancellationToken) {
		if (!Int64.TryParse(principal.FindFirstValue(ClaimTypes.NameIdentifier), out Int64 id)) {
			return null;
		}
		return await database.Users.AsNoTracking().FirstOrDefaultAsync(user => user.Id == id, cancellationToken);
	}

	internal static Boolean IsMaintainer(User? user) => user?.Type is UserType.Admin or UserType.Maintainer;

	internal static ProblemHttpResult Forbidden(String title) => TypedResults.Problem(statusCode: StatusCodes.Status403Forbidden, title: title);

	private static UserResponse ToResponse(User user) => new(user.Id, user.Username, user.FirstName, user.LastName, user.Type);

	private static async Task<Results<SignInHttpResult, ValidationProblem, ProblemHttpResult>> LoginAsync(
		LoginRequest request, AED4LifeDbContext database, IPasswordHasher<User> hasher, CancellationToken cancellationToken) {
		String? username = request.Username?.Trim();
		Dictionary<String, String[]> errors = [];
		if (String.IsNullOrWhiteSpace(username) || username.Length > 255) {
			errors["username"] = ["A username of at most 255 characters is required."];
		}
		if (String.IsNullOrEmpty(request.Password) || request.Password.Length > 1024) {
			errors["password"] = ["A password of at most 1024 characters is required."];
		}
		if (errors.Count > 0) {
			return TypedResults.ValidationProblem(errors);
		}

		ProblemHttpResult invalid = TypedResults.Problem(statusCode: StatusCodes.Status401Unauthorized,
			title: "Invalid username or password.");
		User? user = await database.Users.FirstOrDefaultAsync(candidate => candidate.Username == username, cancellationToken);
		if (user is null) {
			hasher.VerifyHashedPassword(DummyUser, DummyHash, request.Password!);
			return invalid;
		}
		PasswordVerificationResult result = hasher.VerifyHashedPassword(user, user.PasswordHash, request.Password!);
		if (result == PasswordVerificationResult.Failed) {
			return invalid;
		}
		if (result == PasswordVerificationResult.SuccessRehashNeeded) {
			user.PasswordHash = hasher.HashPassword(user, request.Password!);
			await database.SaveChangesAsync(cancellationToken);
		}

		ClaimsIdentity identity = new([
			new Claim(ClaimTypes.NameIdentifier, user.Id.ToString()),
			new Claim(ClaimTypes.Name, user.Username)
		], BearerTokenDefaults.AuthenticationScheme);
		return TypedResults.SignIn(new ClaimsPrincipal(identity), authenticationScheme: BearerTokenDefaults.AuthenticationScheme);
	}

	private static async Task<Results<Ok<UserResponse>, ProblemHttpResult>> GetCurrentUserAsync(
		ClaimsPrincipal principal, AED4LifeDbContext database, CancellationToken cancellationToken) {
		User? user = await GetCallerAsync(principal, database, cancellationToken);
		return user is null
			? TypedResults.Problem(statusCode: StatusCodes.Status401Unauthorized, title: "The user no longer exists.")
			: TypedResults.Ok(ToResponse(user));
	}

	private static async Task<Results<Ok<List<UserResponse>>, ProblemHttpResult>> GetUsersAsync(
		ClaimsPrincipal principal, AED4LifeDbContext database, CancellationToken cancellationToken) {
		User? caller = await GetCallerAsync(principal, database, cancellationToken);
		if (caller?.Type != UserType.Admin) {
			return Forbidden("Only administrators can list users.");
		}
		List<UserResponse> users = await database.Users.AsNoTracking().OrderBy(user => user.Username)
			.Select(user => new UserResponse(user.Id, user.Username, user.FirstName, user.LastName, user.Type))
			.ToListAsync(cancellationToken);
		return TypedResults.Ok(users);
	}

	private static async Task<Results<Ok<UserResponse>, ProblemHttpResult>> PromoteAsync(
		Int64 id, ClaimsPrincipal principal, AED4LifeDbContext database, CancellationToken cancellationToken) {
		User? caller = await GetCallerAsync(principal, database, cancellationToken);
		if (caller?.Type != UserType.Admin) {
			return Forbidden("Only administrators can promote users.");
		}
		User? target = await database.Users.FirstOrDefaultAsync(user => user.Id == id, cancellationToken);
		if (target is null) {
			return TypedResults.Problem(statusCode: StatusCodes.Status404NotFound, title: "The specified user does not exist.");
		}
		if (target.Type == UserType.Admin) {
			return TypedResults.Problem(statusCode: StatusCodes.Status409Conflict, title: "Administrators cannot be changed to maintainers.");
		}
		if (target.Type != UserType.Maintainer) {
			target.Type = UserType.Maintainer;
			await database.SaveChangesAsync(cancellationToken);
		}
		return TypedResults.Ok(ToResponse(target));
	}
}
