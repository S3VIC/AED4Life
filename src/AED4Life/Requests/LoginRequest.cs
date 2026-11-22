using System.Text.Json.Serialization;

namespace AED4Life.Requests;

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record LoginRequest(String? Username, String? Password);
