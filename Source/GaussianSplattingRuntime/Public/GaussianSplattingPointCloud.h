#pragma once

#include "UObject/NoExportTypes.h"
#include "NiagaraDataInterfaceCurve.h"
#include "GaussianSplattingPointCloud.generated.h"


UENUM() 
enum class EGaussianSplattingCompressionMethod : uint8
{
	None,
	Zlib,
};

USTRUCT(BlueprintType, meta = (DisplayName = "Gaussian Splatting Point"))
struct GAUSSIANSPLATTINGRUNTIME_API FGaussianSplattingPoint
{
	GENERATED_BODY()
public:
	UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "Gaussian Splatting")
	FVector3f Position;

	UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "Gaussian Splatting")
	FQuat4f Quat;

	UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "Gaussian Splatting")
	FVector3f Scale;

	UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "Gaussian Splatting")
	FLinearColor Color;

	UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "Gaussian Splatting")
	FVector4f Time;

	UPROPERTY(BlueprintReadWrite, EditAnywhere, Category = "Gaussian Splatting")
	FVector4f Motion;

	FGaussianSplattingPoint(FVector3f InPos = FVector3f::ZeroVector,
		FQuat4f InQuat = FQuat4f::Identity,
		FVector3f InScale = { 1,1,1 },
		FLinearColor InColor = FLinearColor::Black,
		FVector4f InTime = FVector4f(0.f, 0.f, 0.f, 0.f),
		FVector4f InMotion = FVector4f(0.f, 0.f, 0.f, 0.f));

	bool operator==(const FGaussianSplattingPoint& Other)const;
	bool operator!=(const FGaussianSplattingPoint& Other)const;
	bool operator<(const FGaussianSplattingPoint& Other)const;

	friend FORCEINLINE uint32 GetTypeHash(const FGaussianSplattingPoint& ID)
	{
		return	HashCombine(
			HashCombine(
				HashCombine(
					HashCombine(
						HashCombine(
							GetTypeHash(ID.Position),
							GetTypeHash(ID.Quat)),
						GetTypeHash(ID.Scale)),
					GetTypeHash(ID.Color)),
				GetTypeHash(ID.Time)),
			GetTypeHash(ID.Motion));
	}

	friend FORCEINLINE FArchive& operator<<(FArchive& Ar, FGaussianSplattingPoint& Point)
	{
		Ar << Point.Position;
		Ar << Point.Quat;
		Ar << Point.Scale;
		Ar << Point.Color;
		Ar << Point.Time;
		Ar << Point.Motion;
		return Ar;
	}
};

UCLASS(Blueprintable, BlueprintType, EditInlineNew, CollapseCategories)
class GAUSSIANSPLATTINGRUNTIME_API UGaussianSplattingPointCloud : public UObject {
	GENERATED_UCLASS_BODY()
public:
	FSimpleMulticastDelegate OnPointsChanged;

	FRichCurve CalcFeatureCurve();

	FBox CalcBounds();

	void SetPoints(const TArray<FGaussianSplattingPoint>& InPoints, bool bReorder = true);

	const TArray<FGaussianSplattingPoint>& GetPoints() const;

	int32 GetPointCount() const;

	void LoadFromFile(FString InFilePath);

	static TArray<FGaussianSplattingPoint> LoadPointsFromFile(FString InFilePath);

	EGaussianSplattingCompressionMethod GetCompressionMethod() const { return CompressionMethod; }

	void SetCompressionMethod(EGaussianSplattingCompressionMethod val) { CompressionMethod = val; }

private:
	void Serialize(FArchive& Ar) override;

private:
	UPROPERTY(EditAnywhere, Category = "Gaussian Splatting")
	EGaussianSplattingCompressionMethod CompressionMethod = EGaussianSplattingCompressionMethod::Zlib;

	UPROPERTY(Transient)
	TArray<FGaussianSplattingPoint> Points;

	UPROPERTY()
	uint32 FeatureLevel = 64;
};
