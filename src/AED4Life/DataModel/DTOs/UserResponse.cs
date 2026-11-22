using AED4Life.DataModel.Enums;

namespace AED4Life.DataModel.DTOs;

public sealed record UserResponse(Int64 Id, String Username, String FirstName, String LastName, UserType Type);
