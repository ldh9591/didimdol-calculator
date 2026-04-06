import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

# 1. KB국민은행 디딤돌 금리 데이터
INTEREST_RATES = {
    "2천 이하": {10: 2.40, 15: 2.45, 20: 2.55, 30: 2.70, 40: 2.80},
    "2천~4천": {10: 2.80, 15: 2.85, 20: 2.95, 30: 3.10, 40: 3.20},
    "4천~7천": {10: 3.20, 15: 3.25, 20: 3.35, 30: 3.50},
    "7천~8.5천": {10: 3.55, 15: 3.60, 20: 3.70, 30: 3.85},
    "8.5천~1억": {10: 3.90, 15: 3.95, 20: 4.05, 30: 4.15},
}

# 2. 인기 배당주 사전 (우량주 필터링 풀)
POPULAR_STOCKS = {
    "🇺🇸 리얼티 인컴 (O)": "O",
    "🇺🇸 SCHD (미국 우량 배당 ETF)": "SCHD",
    "🇺🇸 JEPI (고배당 커버드콜)": "JEPI",
    "🇺🇸 코카콜라 (KO)": "KO",
    "🇺🇸 마이크로소프트 (MSFT)": "MSFT",
    "🇰🇷 맥쿼리인프라 (088980)": "088980.KS",
    "🇰🇷 삼성전자우 (005935)": "005935.KS",
    "🇰🇷 기업은행 (024110)": "024110.KS"
}

# 3. 데이터 수집 함수 (뻥튀기 버그 수정 완료)
@st.cache_data(ttl=3600)
def get_dividend_yield(ticker):
    try:
        stock = yf.Ticker(ticker)
        div_yield = stock.info.get('dividendYield')
        if div_yield is None:
            div_yield = stock.info.get('trailingAnnualDividendYield')
            
        if div_yield is not None:
            if div_yield > 0.3: # 이미 % 단위로 온 경우
                return float(div_yield)
            else: # 소수점으로 온 경우
                return float(div_yield) * 100
        else:
            return 0.0
    except:
        return 0.0

def main():
    st.set_page_config(page_title="디딤돌 포트폴리오 최적화", layout="wide")
    st.title("🏠 디딤돌 이자 방어: 스마트 자산 배분기")
    
    # ──────────────────────────────────────────────
    # 사이드바: 대출 조건 설정
    # ──────────────────────────────────────────────
    with st.sidebar:
        st.header("📝 대출 조건 설정")
        loan_amount = st.number_input("대출 금액 (원)", value=280_000_000, step=10_000_000)
        income_tier = st.selectbox("연소득 구간", list(INTEREST_RATES.keys()), index=2)
        loan_term = st.selectbox("대출 기간 (년)", [10, 15, 20, 30, 40], index=3)
        
        base_rate = INTEREST_RATES[income_tier].get(loan_term, 3.50) if not (loan_term == 40 and income_tier not in ["2천 이하", "2천~4천"]) else 0.0
        rate_type = st.radio("금리 방식", ["변동 (0.1%p)", "10년 고정 (0.2%p)", "순수 고정 (0.3%p)"], index=2)
        add_rate = 0.3 if "순수 고정" in rate_type else 0.2 if "10년 고정" in rate_type else 0.1
        
        is_rural = st.checkbox("지방 소재 (0.2%p 인하)")
        total_discount = (0.1 if st.checkbox("신규 결혼 (0.1%p)") else 0) + \
                         (0.5 if st.checkbox("최초 출산 (0.5%p)") else 0) + \
                         (0.2 if st.checkbox("추가 출산 (0.2%p)") else 0)
        
        final_rate = max(1.5, base_rate + add_rate - (0.2 if is_rural else 0.0) - total_discount)
        st.info(f"✅ 적용 대출 금리: 연 {final_rate:.2f}%")

    be_yield = (final_rate / (1 - 0.154)) if loan_amount > 0 else 0

    # ──────────────────────────────────────────────
    # 메인: 장바구니 종목 선택
    # ──────────────────────────────────────────────
    st.subheader("🛒 우량 배당주 장바구니 담기")
    inv_amount = st.number_input("총 투자 원금 (원)", value=loan_amount, step=10_000_000)
    st.write(f"💡 **목표:** 이자를 100% 방어하려면 포트폴리오 종합 배당률이 최소 **{be_yield:.2f}%** 이상이어야 합니다.")

    selected_names = st.multiselect(
        "1️⃣ 검증된 우량 배당주 리스트에서 고르기",
        options=list(POPULAR_STOCKS.keys()),
        default=["🇺🇸 리얼티 인컴 (O)", "🇺🇸 SCHD (미국 우량 배당 ETF)", "🇰🇷 삼성전자우 (005935)"]
    )
    custom_ticker = st.text_input("2️⃣ 리스트에 없는 종목 직접 추가 (티커 입력 후 엔터)", placeholder="예: AAPL, 058470.KQ")

    tickers = [POPULAR_STOCKS[name] for name in selected_names]
    if custom_ticker:
        custom_list = [t.strip().upper() for t in custom_ticker.split(",") if t.strip()]
        tickers.extend(custom_list)
    tickers = list(dict.fromkeys(tickers)) # 중복 제거

    # ──────────────────────────────────────────────
    # 알고리즘: 자산 비중 최적화 로직
    # ──────────────────────────────────────────────
    if tickers:
        st.divider()
        st.subheader("🤖 알고리즘 자산 비중 조절기")
        
        raw_data = []
        for t in tickers:
            y = get_dividend_yield(t)
            raw_data.append({"종목(Ticker)": t, "배당수익률(%)": round(y, 2)})
            
        df_base = pd.DataFrame(raw_data)
        
        opt_mode = st.radio(
            "최적화 방식을 선택하세요:", 
            ["⚖️ 1/N 균등 분배", "💰 고배당 몰빵 (위험)", "🛡️ 스마트 이자 방어 (추천!)"],
            horizontal=True, index=2
        )

        n = len(df_base)
        weights = []
        
        if opt_mode == "⚖️ 1/N 균등 분배":
            weights = [100 / n] * n
            
        elif opt_mode == "💰 고배당 몰빵 (위험)":
            total_yield = df_base["배당수익률(%)"].sum()
            weights = [(y / total_yield) * 100 if total_yield > 0 else (100/n) for y in df_base["배당수익률(%)"]]
            
        elif opt_mode == "🛡️ 스마트 이자 방어 (추천!)":
            # 종목이 너무 많으면 기본 마진율 조정
            min_weight = min(10.0, 100.0 / n) 
            weights = [min_weight] * n
            remaining_weight = 100.0 - (min_weight * n)
            
            # 수익률 내림차순 정렬 (공격수 -> 수비수)
            sorted_indices = df_base["배당수익률(%)"].argsort()[::-1]
            
            for idx in sorted_indices:
                if remaining_weight <= 0:
                    break
                current_port_yield = sum(df_base.loc[i, "배당수익률(%)"] * (weights[i]/100) for i in range(n))
                
                if current_port_yield >= be_yield:
                    safest_idx = sorted_indices[-1] # 수익률 가장 낮은 종목(안전 자산)
                    weights[safest_idx] += remaining_weight
                    remaining_weight = 0
                    break
                else:
                    # 한 종목당 최대 50%까지만 제한 (분산 투자)
                    add_w = min(remaining_weight, 50.0 - min_weight) 
                    weights[idx] += add_w
                    remaining_weight -= add_w
            
            if remaining_weight > 0:
                for i in range(n):
                    weights[i] += remaining_weight / n

        df_base["투자 비중(%)"] = [round(w, 1) for w in weights]
        
        col1, col2 = st.columns([1.5, 1])
        
        with col1:
            st.caption("👇 계산된 비중입니다. 원하는 대로 숫자를 더블클릭해서 수정해보세요.")
            edited_df = st.data_editor(df_base, num_rows="dynamic", use_container_width=True)
            
            total_weight = edited_df["투자 비중(%)"].sum()
            if abs(total_weight - 100) > 0.1:
                st.error(f"⚠️ 투자 비중의 합이 100%가 아닙니다. (현재 합계: {total_weight:.1f}%)")
                return 

            portfolio_yield = sum((row["배당수익률(%)"] * row["투자 비중(%)"] / 100) for _, row in edited_df.iterrows())
            
        with col2:
            fig_pie = go.Figure(data=[go.Pie(labels=edited_df["종목(Ticker)"], values=edited_df["투자 비중(%)"], hole=.3)])
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250)
            st.plotly_chart(fig_pie, use_container_width=True)

        # ──────────────────────────────────────────────
        # 최종 결과 및 월간 현금흐름
        # ──────────────────────────────────────────────
        st.divider()
        monthly_loan_interest = (loan_amount * (final_rate / 100)) / 12
        monthly_div_net = (inv_amount * (portfolio_yield / 100) * (1 - 0.154)) / 12
        monthly_profit = monthly_div_net - monthly_loan_interest

        st.subheader(f"🏆 최종 포트폴리오 예상 배당수익률: {portfolio_yield:.2f}%")
        
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("월 대출 이자", f"{monthly_loan_interest:,.0f}원")
        res_col2.metric("월 세후 배당금", f"{monthly_div_net:,.0f}원")
        res_col3.metric("최종 월 순수익", f"{monthly_profit:,.0f}원", 
                  delta=f"{monthly_profit:,.0f}원" if monthly_profit >= 0 else f"{monthly_profit:,.0f}원",
                  delta_color="normal" if monthly_profit >= 0 else "inverse")
                  
        st.info("💡 **전략 요약:** 알고리즘이 입력하신 우량주 중에서 대출 이자를 낼 수 있는 최소한의 고배당주를 채운 뒤, 남은 모든 투자금을 가장 안전한(수익률이 가장 낮은) 주식으로 대피시켰습니다.")

if __name__ == "__main__":
    main()
