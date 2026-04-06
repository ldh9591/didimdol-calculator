import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 1. KB국민은행 디딤돌 금리 데이터 (2026.01.01 기준)
INTEREST_RATES = {
    "2천 이하": {10: 2.40, 15: 2.45, 20: 2.55, 30: 2.70, 40: 2.80},
    "2천~4천": {10: 2.80, 15: 2.85, 20: 2.95, 30: 3.10, 40: 3.20},
    "4천~7천": {10: 3.20, 15: 3.25, 20: 3.35, 30: 3.50},
    "7천~8.5천": {10: 3.55, 15: 3.60, 20: 3.70, 30: 3.85},
    "8.5천~1억": {10: 3.90, 15: 3.95, 20: 4.05, 30: 4.15},
}

def main():
    st.set_page_config(page_title="디딤돌 배당 차익 계산기", layout="wide")
    st.title("🏠 디딤돌 대출 이자 vs 배당 수익 판독기")
    st.caption("대출받은 돈으로 배당주에 투자했을 때의 실질 현금흐름을 계산합니다.")

    # ──────────────────────────────────────────────
    # 사이드바: 대출 조건 설정
    # ──────────────────────────────────────────────
    with st.sidebar:
        st.header("📝 대출 조건 설정")
        loan_amount = st.number_input("대출 금액 (원)", value=280_000_000, step=10_000_000, format="%d")
        
        income_tier = st.selectbox("부부합산 연소득 구간", list(INTEREST_RATES.keys()), index=2)
        loan_term = st.selectbox("대출 기간 (년)", [10, 15, 20, 30, 40], index=3)
        
        if loan_term == 40 and income_tier not in ["2천 이하", "2천~4천"]:
            st.error("⚠️ 40년 만기는 연소득 4천만 원 이하만 선택 가능합니다.")
            base_rate = 0.0
        else:
            base_rate = INTEREST_RATES[income_tier].get(loan_term, 3.50)

        is_rural = st.checkbox("대출 주택이 지방 소재 (0.2%p 인하)", value=False)
        rate_type = st.radio("금리 방식 (가산)", ["변동금리 (0.1%p)", "10년 고정후 변동 (0.2%p)", "순수 고정금리 (0.3%p)"], index=2)
        
        # 가산/우대 금리 계산
        add_rate = 0.3 if "순수 고정" in rate_type else 0.2 if "10년 고정" in rate_type else 0.1
        rural_discount = 0.2 if is_rural else 0.0
        
        st.subheader("🎁 우대금리 (중복가능)")
        u1 = st.checkbox("신규 결혼 (0.1%p)")
        u2 = st.checkbox("최초 출산 (0.5%p)")
        u3 = st.checkbox("추가 출산 (0.2%p)")
        
        total_discount = (0.1 if u1 else 0) + (0.5 if u2 else 0) + (0.2 if u3 else 0)
        final_rate = max(1.5, base_rate + add_rate - rural_discount - total_discount)

        st.info(f"✅ 적용 대출 금리: 연 {final_rate:.2f}%")

    # ──────────────────────────────────────────────
    # 메인 화면: 투자 조건 및 결과
    # ──────────────────────────────────────────────
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 배당 투자 설정")
        inv_amount = st.number_input("투자 원금 (원)", value=loan_amount, step=10_000_000, format="%d")
        div_yield = st.slider("예상 연 배당률 (%)", 1.0, 12.0, 4.5, 0.1)
        st.caption("배당소득세 15.4%가 자동으로 차감되어 계산됩니다.")

    # 계산 로직
    monthly_loan_interest = (loan_amount * (final_rate / 100)) / 12
    monthly_div_net = (inv_amount * (div_yield / 100) * (1 - 0.154)) / 12
    monthly_profit = monthly_div_net - monthly_loan_interest
    
    # 손익분기점 배당률 역산
    be_yield = (monthly_loan_interest * 12) / (inv_amount * (1 - 0.154)) * 100

    with col2:
        st.subheader("💰 월간 현금흐름 결과")
        res_col1, res_col2 = st.columns(2)
        res_col1.metric("월 대출 이자", f"{monthly_loan_interest:,.0f}원")
        res_col2.metric("월 세후 배당금", f"{monthly_div_net:,.0f}원")
        
        color = "normal" if monthly_profit >= 0 else "inverse"
        st.metric("최종 월 순수익 (이자 방어 후)", f"{monthly_profit:,.0f}원", 
                  delta=f"{monthly_profit:,.0f}원" if monthly_profit >= 0 else f"{monthly_profit:,.0f}원",
                  delta_color=color)

    st.divider()

    # 시각화
    fig = go.Figure()
    fig.add_trace(go.Bar(name="비용 (이자)", x=["월간 흐름"], y=[monthly_loan_interest], marker_color="#ef4444"))
    fig.add_trace(go.Bar(name="수익 (배당)", x=["월간 흐름"], y=[monthly_div_net], marker_color="#3b82f6"))
    fig.update_layout(barmode='group', height=400, title="이자 vs 배당금 비교", yaxis_tickformat=",")
    st.plotly_chart(fig, use_container_width=True)

    # 💡 전략 판독 메시지
    st.subheader("📝 전문가의 전략 판독")
    if monthly_profit > 0:
        st.success(f"✅ **성공적인 전략입니다!** 매달 이자를 다 내고도 **{monthly_profit:,.0f}원**이 남습니다.")
        st.write(f"- 이자를 100% 방어하기 위한 최소 배당률은 **{be_yield:.2f}%**입니다. 현재 포트폴리오가 넉넉합니다.")
    else:
        st.warning(f"⚠️ **주의!** 매달 **{abs(monthly_profit):,.0f}원**의 추가 지출이 발생합니다.")
        st.write(f"- 이자를 완벽히 방어하려면 배당률을 **{be_yield:.2f}%**까지 끌어올려야 합니다.")

    with st.expander("📌 자산 기준 체크 (5.11억)"):
        net_asset = (400_000_000 + inv_amount) - loan_amount  # 집값 4억 가정
        st.write(f"현재 예상 순자산: 약 **{net_asset/1e8:.2f}억 원**")
        if net_asset > 511_000_000:
            st.error("🚨 자산 기준(5.11억) 초과 가능성이 높습니다! 금리가 가산될 수 있으니 주의하세요.")
        else:
            st.info("✅ 자산 기준 내에 있어 안전한 구간입니다.")

if __name__ == "__main__":
    main()