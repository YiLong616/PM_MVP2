import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 必須是第一個呼叫的 Streamlit 函式，設定網頁標題與寬度
st.set_page_config(page_title="Alt-Data Credit Engine", layout="wide")

# ==========================================
# 1. 資料層 Data Layer (模擬供應鏈數據)
# ==========================================
@st.cache_data
def load_sme_data():
    # 建立中小企業的供應鏈營運模擬數據
    smes = pd.DataFrame({
        'SME_ID': ['SME-001', 'SME-002', 'SME-003', 'SME-004'],
        'Company_Name': ['Tech Innovators Inc.', 'Global Components Ltd.', 'Apex Retail Supply', 'Pioneer Materials'],
        'Fill_Rate_Pct': [98, 85, 92, 65],          # 訂單完成率 (越高越好)
        'Defect_Rate_Pct': [1.2, 4.5, 2.0, 9.5],    # 瑕疵率 (越低越好)
        'Cust_Concentration_Pct': [35, 80, 45, 95], # 客戶集中度 (越低風險越小)
        'Inv_Turnover_Days': [30, 60, 40, 120]      # 存貨周轉天數 (越低變現越快)
    })
    return smes

# ==========================================
# 2. 邏輯層 Logic Layer (風險量化計算引擎)
# ==========================================
def calculate_credit_risk(fill, defect, conc, turnover, loan_amount, lgd):
    # --- 數據標準化 (0-100分，分數越高代表風險越低、體質越好) ---
    score_fill = float(fill)
    score_defect = max(0.0, ((10.0 - float(defect)) / 10.0) * 100.0) # 瑕疵率超過10%視為0分
    score_conc = max(0.0, 100.0 - float(conc))
    score_turnover = max(0.0, ((150.0 - float(turnover)) / 150.0) * 100.0) # 周轉天數超過150天視為0分

    # 計算綜合供應鏈健康分數 (加權平均)
    health_score = (score_fill * 0.4) + (score_defect * 0.2) + (score_conc * 0.2) + (score_turnover * 0.2)

    # --- 財務工程運算：預期違約機率 (PD) 與 預期損失 (EL) ---
    # 利用 Logistic 函數將健康分數轉換為違約機率 PD (分數越高，PD越趨近於0)
    pd_rate = 1.0 / (1.0 + np.exp(0.08 * (health_score - 50.0)))

    # 將健康分數映射到傳統信用評分範圍 (300 - 850)，並加入 max/min 限制避免極端值溢出
    alt_credit_score = int(min(850, max(300, 300 + (health_score / 100.0) * 550)))

    # 計算預期損失 Expected Loss (EL = PD * LGD * EAD)
    ead = float(loan_amount)
    el = pd_rate * lgd * ead

    # 動態利率定價 (無風險利率 1.5% + 根據風險調整的溢酬)
    risk_free = 0.015
    recommended_rate = risk_free + (pd_rate * lgd)

    # 自動核貸決策邏輯 (依據替代信用分數)
    if alt_credit_score >= 650:
        decision = "Approved (Low Risk)"
        color = "green"
    elif alt_credit_score >= 550:
        decision = "Manual Review Required"
        color = "orange"
    else:
        decision = "Declined (High Risk)"
        color = "red"

    # 回傳運算結果與繪圖所需的正規化陣列
    return {
        'Alt_Credit_Score': alt_credit_score,
        'PD': pd_rate,
        'EL': el,
        'Recommended_Rate': recommended_rate,
        'Decision': decision,
        'Decision_Color': color,
        'Radar_Scores': [score_fill, score_defect, score_conc, score_turnover]
    }

# ==========================================
# 3. 表現層 Presentation Layer (Streamlit 網頁介面)
# ==========================================

# --- 平台標題與介紹 ---
st.title("📊 SCM Alternative Data Credit Scoring Engine")
st.markdown("**Welcome to the next-generation SME Credit Risk Dashboard.**")

# 使用 st.expander 將說明文字收折，並設定 expanded=False 預設為關閉
with st.expander("💡 How to use this platform (Click to expand)", expanded=False):
    st.markdown("""
    1. **Select Profile:** Choose an SME from the database to load their base SCM metrics.
    2. **Set Loan Terms:** Input the requested loan amount and the proposed collateral (which dynamically alters the Loss Given Default - LGD).
    3. **What-If Simulation:** Use the sliders to stress-test the SME's operational metrics. Watch how changes in defect rates or fulfillment times instantly impact their default probability and expected loss.
    4. **Review Analytics:** Analyze the multi-dimensional radar chart (compared against industry benchmarks) and the final system decision.
    """)
st.markdown("---")

# 載入資料
df_smes = load_sme_data()

# 建立左右兩欄佈局 (左邊設定參數，右邊顯示圖表與結果)
col_left, col_right = st.columns([1, 1.2], gap="large")

with col_left:
    st.subheader("1. Application Details")
    
    # 公司選擇下拉選單
    selected_sme_name = st.selectbox("Company Profile:", df_smes['Company_Name'])
    # 取出被選擇公司的該列數據
    selected_sme = df_smes[df_smes['Company_Name'] == selected_sme_name].iloc[0]
    
    # 貸款金額輸入框
    loan_amount = st.number_input("Requested Loan Amount (USD):", min_value=100000, max_value=5000000, value=1000000, step=100000)
    
    # 擔保品種類選擇，連動改變 LGD (違約損失率)
    collateral_type = st.selectbox("Proposed Collateral:", ["None (Unsecured)", "Accounts Receivable", "Real Estate"])
    lgd_mapping = {"None (Unsecured)": 0.75, "Accounts Receivable": 0.40, "Real Estate": 0.15}
    current_lgd = lgd_mapping[collateral_type]
    st.caption(f"*Calculated Loss Given Default (LGD): {current_lgd*100:.0f}%*")
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("2. What-If Scenario Simulation")
    
    # 動態滑桿 (利用 help 參數加入 Hint Tooltip，讓 UI 更乾淨)
    sim_fill = st.slider(
        "Order Fill Rate (%)", 0, 100, int(selected_sme['Fill_Rate_Pct']),
        help="Higher is better. Measures the percentage of customer orders fulfilled without stockouts or backorders."
    )
    sim_defect = st.slider(
        "Defect Rate (%)", 0.0, 15.0, float(selected_sme['Defect_Rate_Pct']), step=0.1,
        help="Lower is better. Represents the percentage of products that fail quality control."
    )
    sim_conc = st.slider(
        "Customer Concentration (%)", 0, 100, int(selected_sme['Cust_Concentration_Pct']),
        help="Lower is better. A high percentage indicates over-reliance on a few major clients, increasing revenue risk."
    )
    sim_turnover = st.slider(
        "Inventory Turnover (Days)", 10, 180, int(selected_sme['Inv_Turnover_Days']),
        help="Lower is better. Shows how many days it takes to sell the inventory. Faster turnover means better liquidity."
    )

with col_right:
    st.subheader("3. Risk Analytics & Decision")
    
    # 呼叫風險運算引擎，帶入滑桿的動態數值與 LGD
    risk_results = calculate_credit_risk(sim_fill, sim_defect, sim_conc, sim_turnover, loan_amount, current_lgd)
    
    # --- 繪製雷達圖 (Radar Chart) ---
    categories = ['Order Fulfillment', 'Quality Control', 'Customer Diversity', 'Inventory Agility']
    # 將數據頭尾相連以閉合雷達圖
    radar_values = risk_results['Radar_Scores'] + [risk_results['Radar_Scores'][0]] 
    radar_categories = categories + [categories[0]]
    
    # 模擬產業平均分數基準線
    industry_avg = [75, 70, 60, 65] 
    industry_radar_values = industry_avg + [industry_avg[0]]

    fig = go.Figure()
    
    # 圖層 1: 產業平均值 (灰色虛線)
    fig.add_trace(go.Scatterpolar(
        r=industry_radar_values,
        theta=radar_categories,
        fill='toself',
        fillcolor='rgba(169, 169, 169, 0.2)',
        line=dict(color='gray', dash='dash'),
        name='Industry Average'
    ))
    
    # 圖層 2: 該企業動態數據 (藍色實線)
    fig.add_trace(go.Scatterpolar(
        r=radar_values,
        theta=radar_categories,
        fill='toself',
        fillcolor='rgba(65, 105, 225, 0.5)',
        line_color='royalblue',
        name=selected_sme_name
    ))
    
    # 雷達圖版面設定
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1),
        margin=dict(t=50, b=30, l=30, r=30)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # --- 顯示計量財務輸出結果 ---
    st.markdown(f"### System Decision: :{risk_results['Decision_Color']}[**{risk_results['Decision']}**]")
    
    r1, r2 = st.columns(2)
    r1.metric("Alternative Credit Score", risk_results['Alt_Credit_Score'])
    r2.metric("Probability of Default (PD)", f"{risk_results['PD'] * 100:.2f}%")
    
    r3, r4 = st.columns(2)
    # 金額加入千分位逗號格式化
    r3.metric("Expected Loss (EL)", f"${risk_results['EL']:,.0f}")
    r4.metric("Recommended Interest Rate", f"{risk_results['Recommended_Rate'] * 100:.2f}%")
