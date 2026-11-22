namespace AED4Life.DataModel.DTOs;

/// <summary>Valid = <c>DataRating == Fine</c>; ValidPercentage = Valid / Total * 100, rounded to two decimals (0 when empty).</summary>
public sealed record AEDStatisticsResponse(Int32 Total, Int32 Valid, Int32 MissingData, Int32 Unknown, Double ValidPercentage);
