import pandas as pd

def ensure_int_col(df, col):
    if col in df.columns:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.strip().replace('', pd.NA),
            errors="coerce"
        ).astype("Int64")
    return df

def read_and_clean_csv(file_path):
    df = pd.read_csv(file_path, low_memory=False)
    df.columns = [c.strip() for c in df.columns]
    return df

def unify_types(df_list):
    for df in df_list:
        ensure_int_col(df, "RACE_NO")
        ensure_int_col(df, "BASE_YEAR")

def check_duplicates(df_register, df_entry):
    print("register duplicates (by PLAYER_NM):", df_register.duplicated(subset=["PLAYER_NM"]).sum())
    if "RACE_NO" in df_entry.columns and "PLAYER_NM" in df_entry.columns:
        print("entry race+player duplicates:", df_entry.duplicated(subset=["RACE_NO", "PLAYER_NM"]).sum())
    else:
        print("df_entry에 RACE_NO 또는 PLAYER_NM 컬럼이 없습니다.")

def merge_dataframes(df_rank, df_register, df_entry):
    # entry + register
    df_entry_merged = df_entry.merge(
        df_register.drop_duplicates("PLAYER_NM"),
        on="PLAYER_NM", how="left", validate="m:1"
    )

    # rank melt 후 병합
    rank_long = melt_rank(df_rank)
    rank_long = map_player_no(rank_long, df_register)

    # full 병합: rank_long + entry
    df_full = rank_long.merge(
        df_entry.drop_duplicates(["RACE_NO", "PLAYER_NM"]),
        on=["RACE_NO", "PLAYER_NM"], how="left", validate="m:1"
    )

    return df_entry_merged, rank_long, df_full

def melt_rank(df_rank):
    rank_long = pd.melt(
        df_rank,
        id_vars=["BASE_YEAR", "RACE_DE", "RACE_NO"],
        value_vars=["N1R_PLAYER_NM", "N2R_PLAYER_NM", "N3R_PLAYER_NM"],
        var_name="RANK_TYPE",
        value_name="PLAYER_NM"
    )
    return rank_long

def map_player_no(rank_long, df_register):
    return rank_long.merge(
        df_register[["PLAYER_NO", "PLAYER_NM"]],
        on="PLAYER_NM",
        how="left"
    )

if __name__ == "__main__":
    # 파일 경로
    rank_path = "KS_CYCR_RACE_RESULT_202507.csv"
    register_path = "KS_CYCR_PLAYER_INFO_202507.csv"
    entry_path = "KS_CYCR_RACE_ORGAN_202508.csv"

    # 데이터 읽기 및 컬럼 정리
    df_rank = read_and_clean_csv(rank_path)
    df_register = read_and_clean_csv(register_path)
    df_entry = read_and_clean_csv(entry_path)

    # 타입 통일
    unify_types([df_rank, df_register, df_entry])

    # 중복 체크
    check_duplicates(df_register, df_entry)

    # 병합
    df_entry_merged, rank_long, df_full = merge_dataframes(df_rank, df_register, df_entry)

    # 결과 확인
    print("entry+register 병합 결과:", df_entry_merged.shape)
    print("rank melt 결과:", rank_long.shape)
    print("전체 병합 결과:", df_full.shape)
