import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ==========================================
# 1. Data Layer (模擬供應鏈替代數據)
# ==========================================

@st.cache_data
def load_sme_data():
    # 建立中小企業 (SME) 的供應鏈營運數據
    smes = pd.DataFrame({
        'SME_ID': ['SME-001', 'SME-002', 'SME-003', 'SME-004'],
        'Company_Name': ['Tech Innovators Inc.', 'Global Components Ltd.', 'Apex Retail Supply', 'Pioneer Materials'],
        'Fill_Rate_Pct': [98, 85, 92, 65],          # 訂單完成率 (%) - 高較好
        'Defect_Rate_Pct': [1.2, 4.5, 2.0, 9.5],    # 瑕疵率 (%) - 低較好
        'Cust_Concentration_Pct': [35, 80, 45, 95], # 客戶集中度 (%) - 低較好 (代表客源分散)
        'Inv_Turnover_Days': [30, 60, 40, 120]      # 存貨周轉天數 (Days) - 低較好 (代表變現快)
    })
    return smes

# ==========================================
# 2. Logic Layer (統計與信用風險量化引擎)
# ==========================================

def calculate_credit_risk(sme_data, loan_amount):
    # 取得原始數據
    fill = sme_data['Fill_Rate_Pct']
    defect = sme_data['Defect_Rate_Pct']
    conc = sme_data['Cust_Concentration_Pct']
    turnover = sme_data['Inv_Turnover_Days']

    # --- 統計學應用：數據標準化 (0-100分，分數越高代表風險越低、體質越好) ---
    score_fill = fill
    score_defect = max(0, ((10 - defect) / 10) * 100) # 假設瑕疵率超過10%為0分
    score_conc = max(0, 100 - conc)
    score_turnover = max(0, ((150 - turnover) / 150) * 100) # 假設周轉天數超過150天為0分

    # 計算綜合供應鏈健康分數 (加權平均)
    health_score = (score_fill * 0.4) + (score_defect * 0.2) + (score_conc * 0.2) + (score_turnover * 0.2)

    # --- 計量金融應用：預期違約機率 (PD) 與預期損失 (EL) ---
    # 利用 Logistic 函數將健康分數轉換為違約機率 (PD)
    pd_rate = 1 / (1 + np.exp(0.08 * (health_score - 50)))

    # 將健康分數映射到傳統的信用評分範圍 (300 - 850)
    alt_credit_score = int(300 + (health_score / 100) * 550)

    # 計算預期損失 Expected Loss (EL = PD * LGD * EAD)
    lgd = 0.45 # 假設違約損失率為 45%
    ead = loan_amount # 違約暴險額即為貸款金額
    el = pd_rate * lgd * ead

    # 動態利率定價 (無風險利率 1.5% + 風險溢酬)
    risk_free = 0.015
    recommended_rate = risk_free + (pd_rate * lgd)

    # 自動核貸決策邏輯
    if alt_credit_score >= 650:
        decision = "Approved (Low Risk)"
        color = "green"
    elif alt_credit_score >= 550:
        decision = "Manual Review Required"
        color = "orange"
    else:
        decision = "Declined (High Risk)"
        color = "red"

    return {
        'Alt_Credit_Score': alt_credit_score,
        'PD': pd_rate,
        'EL': el,
        'Recommended_Rate': recommended_rate,
        'Decision': decision,
        'Decision_Color': color,
        # 回傳雷達圖需要的標準化各項分數
        'Radar_Scores': [score_fill, score_defect, score_conc, score_turnover]
    }

# ==========================================
# 3. Presentation Layer (Streamlit 網頁介面)
# ==========================================

st.set_page_config(page_title="Alternative Credit Scoring MVP", layout="wide")
st.title("📊 SCM Alternative Data Credit Scoring Engine")
st.markdown("Assess SME credit risk using Supply Chain Management metrics instead of traditional financial statements.")

# 初始化資料
df_smes = load_sme_data()

# 建立左右兩欄佈局
col_left, col_right = st.columns([1, 1.2])

with col_left:
    st.subheader("1. Select SME & Loan Details")
    
    # 下拉選單選擇企業
    selected_sme_name = st.selectbox("Select an SME to Evaluate:", df_smes['Company_Name'])
    selected_sme = df_smes[df_smes['Company_Name'] == selected_sme_name].iloc[0]
    
    # 輸入欲申請的貸款金額
    loan_amount = st.number_input("Requested Loan Amount (USD):", min_value=100000, max_value=5000000, value=1000000, step=100000)
    
    st.markdown("---")
    st.subheader("2. Raw Supply Chain Metrics")
    
    # 顯示原始供應鏈數據
    m1, m2 = st.columns(2)
    m1.metric("Order Fill Rate", f"{selected_sme['Fill_Rate_Pct']}%")
    m2.metric("Defect Rate", f"{selected_sme['Defect_Rate_Pct']}%")
    
    m3, m4 = st.columns(2)
    m3.metric("Customer Concentration", f"{selected_sme['Cust_Concentration_Pct']}%")
    m4.metric("Inventory Turnover", f"{selected_sme['Inv_Turnover_Days']} Days")

with col_right:
    st.subheader("3. Alternative Credit Risk Analysis")
    
    # 呼叫風險運算引擎
    risk_results = calculate_credit_risk(selected_sme, loan_amount)
    
    # --- 繪製雷達圖 (Radar Chart) ---
    categories = ['Order Fulfillment', 'Quality Control', 'Customer Diversity', 'Inventory Agility']
    # 將數值頭尾相連以閉合雷達圖
    radar_values = risk_results['Radar_Scores'] + [risk_results['Radar_Scores'][0]]
    radar_categories = categories + [categories[0]]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=radar_values,
        theta=radar_categories,
        fill='toself',
        name=selected_sme['Company_Name'],
        line_color='royalblue'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        margin=dict(t=30, b=30, l=30, r=30)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # --- 顯示計量金融輸出結果 ---
    st.markdown(f"### System Decision: :{risk_results['Decision_Color']}[{risk_results['Decision']}]")
    
    r1, r2 = st.columns(2)
    r1.metric("Alternative Credit Score", risk_results['Alt_Credit_Score'])
    r2.metric("Probability of Default (PD)", f"{risk_results['PD'] * 100:.2f}%")
    
    r3, r4 = st.columns(2)
    r3.metric("Expected Loss (EL)", f"${risk_results['EL']:,.0f}")
    r4.metric("Recommended Interest Rate", f"{risk_results['Recommended_Rate'] * 100:.2f}%")