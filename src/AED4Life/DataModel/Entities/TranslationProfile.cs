namespace AED4Life.DataModel.Entities;

public class TranslationProfile {
	public Int64 Id { get; set; }
	public required String Name { get; set; }
	public List<TranslationProfileUnit> Units { get; set; } = [];
}
