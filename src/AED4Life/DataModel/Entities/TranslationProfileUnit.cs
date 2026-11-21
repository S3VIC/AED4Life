using AED4Life.Trananslation;

namespace AED4Life.DataModel.Entities;

public class TranslationProfileUnit {
	public Int64 Id { get; set; }
	public Int64 TranslationProfileId { get; set; }
	public Int32 Position { get; set; }
	public required String FromColumn { get; set; }
	public VariableType FromType { get; set; }
	public required String ToColumn { get; set; }
	public VariableType ToType { get; set; }
}
