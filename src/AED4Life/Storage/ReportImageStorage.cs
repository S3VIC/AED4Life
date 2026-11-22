namespace AED4Life.Storage;

public sealed class ReportImageStorage {
	public const Int64 MaxImageBytes = 5 * 1024 * 1024;
	private readonly String directory;
	private readonly ILogger<ReportImageStorage> logger;

	public ReportImageStorage(IConfiguration configuration, IWebHostEnvironment environment, ILogger<ReportImageStorage> logger) {
		this.logger = logger;
		directory = Path.GetFullPath(configuration["ReportImages:Directory"]
			?? Path.Combine("App_Data", "report-images"), environment.ContentRootPath);
		String webRoot = Path.TrimEndingDirectorySeparator(Path.GetFullPath(
			environment.WebRootPath ?? Path.Combine(environment.ContentRootPath, "wwwroot")));
		StringComparison comparison = OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
		if (directory.Equals(webRoot, comparison) || directory.StartsWith(webRoot + Path.DirectorySeparatorChar, comparison)) {
			throw new InvalidOperationException("ReportImages:Directory must be outside the web root.");
		}
	}

	public async Task<String> SaveAsync(IFormFile image, CancellationToken cancellationToken) {
		if (image.Length == 0) {
			throw new ReportImageValidationException(StatusCodes.Status400BadRequest, "The image file is empty.");
		}
		if (image.Length > MaxImageBytes) {
			throw new ReportImageValidationException(StatusCodes.Status413PayloadTooLarge, "The image must not exceed 5 MiB.");
		}

		await using Stream source = image.OpenReadStream();
		Byte[] header = new Byte[8];
		Int32 headerLength = await source.ReadAtLeastAsync(header, header.Length, false, cancellationToken);
		String extension;
		if (headerLength == 8 && header.AsSpan().SequenceEqual(new Byte[] { 137, 80, 78, 71, 13, 10, 26, 10 })) {
			extension = ".png";
		} else if (headerLength == 8 && header[0] == 255 && header[1] == 216 && header[2] == 255) {
			extension = ".jpg";
		} else {
			throw new ReportImageValidationException(StatusCodes.Status415UnsupportedMediaType, "Only PNG and JPEG image signatures are supported.");
		}
		if (image.Length <= headerLength) {
			throw new ReportImageValidationException(StatusCodes.Status400BadRequest, "The image contains no data beyond its signature.");
		}

		Directory.CreateDirectory(directory);
		String fileName = Guid.NewGuid().ToString("N") + extension;
		Boolean created = false;
		Boolean saved = false;
		try {
			await using (FileStream destination = new(Path.Combine(directory, fileName), FileMode.CreateNew,
				FileAccess.Write, FileShare.None, 81920, FileOptions.Asynchronous)) {
				created = true;
				await destination.WriteAsync(header.AsMemory(0, headerLength), cancellationToken);
				Byte[] buffer = new Byte[81920];
				Int64 total = headerLength;
				Int32 read;
				while ((read = await source.ReadAsync(buffer, cancellationToken)) > 0) {
					total += read;
					if (total > MaxImageBytes) {
						throw new ReportImageValidationException(StatusCodes.Status413PayloadTooLarge, "The image must not exceed 5 MiB.");
					}
					await destination.WriteAsync(buffer.AsMemory(0, read), cancellationToken);
				}
			}
			saved = true;
			return fileName;
		} finally {
			if (created && !saved) {
				Delete(fileName);
			}
		}
	}

	public void Delete(String fileName) {
		try {
			File.Delete(Path.Combine(directory, fileName));
		} catch (Exception exception) when (exception is IOException or UnauthorizedAccessException) {
			logger.LogError(exception, "Could not remove report image {FileName} after a failed report creation.", fileName);
		}
	}
}

public sealed class ReportImageValidationException(Int32 statusCode, String message) : Exception(message) {
	public Int32 StatusCode { get; } = statusCode;
}
