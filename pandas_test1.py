import pandas as pd
import re

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
    df_entry_merged = df_entry.merge(
        df_register.drop_duplicates("PLAYER_NM"),
        on="PLAYER_NM", how="left", validate="m:1"
    )

    rank_long = explode_rank_players(df_rank)
    rank_long = map_player_no(rank_long, df_register)

    df_full = rank_long.merge(
        df_entry.drop_duplicates(["RACE_NO", "PLAYER_NM"]),
        on=["RACE_NO", "PLAYER_NM"], how="left", validate="m:1"
    )

    return df_entry_merged, rank_long, df_full

def clean_player_name(name):
    name = re.sub(r'[①-⑨]', ' ', str(name))  # 기호 제거 후 공백으로 대체
    name = re.sub(r'[^가-힣\s]', '', name)    # 한글과 공백만 남기기
    names = name.strip().split()
    return [n for n in names if len(n) >= 2]


def explode_rank_players(df_rank):
    rank_long = pd.melt(
        df_rank,
        id_vars=["BASE_YEAR", "RACE_DE", "RACE_NO"],
        value_vars=["N1R_PLAYER_NM", "N2R_PLAYER_NM", "N3R_PLAYER_NM"],
        var_name="RANK_TYPE",
        value_name="RAW_PLAYER_NM"
    )
    rank_long["PLAYER_NM_LIST"] = rank_long["RAW_PLAYER_NM"].apply(clean_player_name)
    rank_long = rank_long.explode("PLAYER_NM_LIST").rename(columns={"PLAYER_NM_LIST": "PLAYER_NM"})
    return rank_long

def map_player_no(rank_long, df_register):
    return rank_long.merge(
        df_register[["PLAYER_NO", "PLAYER_NM"]],
        on="PLAYER_NM",
        how="left"
    )

def calculate_win_rate_cleaned(df_rank):
    rank_long = explode_rank_players(df_rank)

    entry_counts = rank_long["PLAYER_NM"].value_counts().rename("ENTRY_COUNT")

    win_names = df_rank["N1R_PLAYER_NM"].dropna().apply(clean_player_name)
    win_names = pd.Series([name for sublist in win_names for name in sublist])
    win_counts = win_names.value_counts().rename("WIN_COUNT")

    win_rate_df = pd.DataFrame(entry_counts).join(win_counts, how="left").fillna(0)
    win_rate_df["WIN_COUNT"] = win_rate_df["WIN_COUNT"].astype(int)
    win_rate_df["WIN_RATE"] = (win_rate_df["WIN_COUNT"] / win_rate_df["ENTRY_COUNT"]).round(4)

    win_rate_df = win_rate_df.reset_index().rename(columns={"index": "PLAYER_NM"})
    win_rate_df = win_rate_df.sort_values(by="WIN_RATE", ascending=False)
    return win_rate_df

if __name__ == "__main__":
    rank_path = "KS_CYCR_RACE_RESULT_202507.csv"
    register_path = "KS_CYCR_PLAYER_INFO_202507.csv"
    entry_path = "KS_CYCR_RACE_ORGAN_202508.csv"

    df_rank = read_and_clean_csv(rank_path)
    df_register = read_and_clean_csv(register_path)
    df_entry = read_and_clean_csv(entry_path)

    unify_types([df_rank, df_register, df_entry])
    check_duplicates(df_register, df_entry)

    df_entry_merged, rank_long, df_full = merge_dataframes(df_rank, df_register, df_entry)

    print("entry+register 병합 결과:", df_entry_merged.shape)
    print("rank melt 결과:", rank_long.shape)
    print("전체 병합 결과:", df_full.shape)

    # 정확한 승률 분석
    win_rate_df = calculate_win_rate_cleaned(df_rank)
    print(win_rate_df.head(10))  # 상위 10명 출력
