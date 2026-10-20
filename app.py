import streamlit as st
import requests
import random
import time

# --- ページ基本設定 ---
st.set_page_config(
    page_title="社会科用語バトル (リアル審判モード)",
    page_icon="🏛️",
    layout="centered"
)

# --- カスタムCSS（用語とスコアを大きく見せるデザイン） ---
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 12px; font-weight: bold; height: 3em; font-size: 1.1rem; }
    .battle-container {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 20px;
    }
    .term-card {
        background-color: #1e293b;
        border: 3px solid #3b82f6;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        flex: 1;
    }
    .term-label { color: #94a3b8; font-size: 0.9rem; font-weight: bold; margin-bottom: 8px; }
    .term-title { color: #fbbf24; font-size: 1.8rem; font-weight: 900; }
    .score-board {
        background-color: #0f172a;
        border: 2px solid #334155;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        color: #f8fafc;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- Secrets からの設定読み込み ---
FIREBASE_URL = st.secrets.get("FIREBASE_DATABASE_URL", "").rstrip("/")

# --- Firebase Realtime Database Helper ---
def fb_put(path, data):
    if not FIREBASE_URL: return
    try:
        requests.put(f"{FIREBASE_URL}/{path}.json", json=data, timeout=5)
    except Exception as e:
        st.error(f"Firebase通信エラー: {e}")

def fb_get(path):
    if not FIREBASE_URL: return None
    try:
        res = requests.get(f"{FIREBASE_URL}/{path}.json", timeout=5)
        return res.json()
    except:
        return None

def fb_patch(path, data):
    if not FIREBASE_URL: return
    try:
        requests.patch(f"{FIREBASE_URL}/{path}.json", json=data, timeout=5)
    except Exception as e:
        st.error(f"Firebase通信エラー: {e}")

# --- セッション状態の初期化 ---
if "page" not in st.session_state: st.session_state.page = "menu"
if "game_type" not in st.session_state: st.session_state.game_type = "online"
if "room_code" not in st.session_state: st.session_state.room_code = ""
if "is_host" not in st.session_state: st.session_state.is_host = True
if "player_name" not in st.session_state: st.session_state.player_name = "プレイヤー1"
if "opponent_name" not in st.session_state: st.session_state.opponent_name = "プレイヤー2"
if "round" not in st.session_state: st.session_state.round = 1
if "score_p1" not in st.session_state: st.session_state.score_p1 = 0
if "score_p2" not in st.session_state: st.session_state.score_p2 = 0

# ==========================================
# 画面ロジック
# ==========================================
st.title("🏛️ 社会科用語・リアル審判バトル")

# --- メニュー画面 ---
if st.session_state.page == "menu":
    st.session_state.player_name = st.text_input("あなたの名前（またはチーム名）", value=st.session_state.player_name)
    
    st.write("---")
    st.markdown("### 📝 このモードについて")
    st.caption("人間がマイクで実況・審判を行います。画面にはお互いの「社会科用語」と「現在のスコア」だけが大きく映し出されます。")
    
    st.write("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏠 ルームを作成 (ホスト)", type="primary", key="btn_create_room"):
            code = str(random.randint(1000, 9999))
            st.session_state.room_code = code
            st.session_state.is_host = True
            st.session_state.round = 1
            st.session_state.score_p1 = 0
            st.session_state.score_p2 = 0
            fb_put(f"rooms/{code}", {
                "host": st.session_state.player_name, "guest": "待機中...",
                "status": "waiting", "round": 1,
                "scoreP1": 0, "scoreP2": 0,
                "hostTerm": "", "guestTerm": ""
            })
            st.session_state.page = "waiting"
            st.rerun()
    with col2:
        input_code = st.text_input("ルームコード(4桁)")
        if st.button("🚪 ルームに参加 (ゲスト)", key="btn_join_room"):
            if input_code:
                data = fb_get(f"rooms/{input_code}")
                if data:
                    st.session_state.room_code = input_code
                    st.session_state.is_host = False
                    st.session_state.round = data.get("round", 1)
                    st.session_state.score_p1 = data.get("scoreP1", 0)
                    st.session_state.score_p2 = data.get("scoreP2", 0)
                    st.session_state.opponent_name = data.get("host", "ホスト")
                    fb_patch(f"rooms/{input_code}", {"guest": st.session_state.player_name})
                    st.session_state.page = "input"
                    st.rerun()
                else: st.error("ルームが見つかりません")

# --- 待機画面（ホスト側） ---
elif st.session_state.page == "waiting":
    st.subheader(f"🏠 ルームコード: {st.session_state.room_code}")
    st.info("対戦相手の入室を待っています...")
    time.sleep(2)
    data = fb_get(f"rooms/{st.session_state.room_code}")
    if data and data.get("guest") and data.get("guest") != "待機中...":
        st.session_state.opponent_name = data["guest"]
        st.success(f"{data['guest']} さんが参加しました！")
        time.sleep(1)
        st.session_state.page = "input"
        st.rerun()
    else:
        st.rerun()

# --- 用語入力画面 ---
elif st.session_state.page == "input":
    st.subheader(f"⚔️ 第 {st.session_state.round} ラウンド / 全3戦")
    
    # スコアボード表示
    host_n = st.session_state.player_name if st.session_state.is_host else st.session_state.opponent_name
    guest_n = st.session_state.opponent_name if st.session_state.is_host else st.session_state.player_name
    st.markdown(f"<div class='score-board'>{host_n} 【 {st.session_state.score_p1} 勝 】 - 【 {st.session_state.score_p2} 勝 】 {guest_n}</div>", unsafe_allow_html=True)
    
    st.info("💡 自分が出す社会科用語を入力してください（両者が提出するとお互いの画面に大きくオープンされます！）")

    with st.form("term_form"):
        my_term = st.text_input("あなたの勝負用語", placeholder="例：ハンムラビ法典、カルスト地形 など")
        submit = st.form_submit_button("🔥 用語を決定してロックする！", type="primary")
        
        if submit:
            if not my_term.strip():
                st.error("用語を入力してください。")
            else:
                role = "host" if st.session_state.is_host else "guest"
                fb_patch(f"rooms/{st.session_state.room_code}", {
                    f"{role}Term": my_term
                })
                st.session_state.page = "wait_opponent"
                st.rerun()

# --- 相手の入力待ち画面 ---
elif st.session_state.page == "wait_opponent":
    st.subheader(f"⏳ 第 {st.session_state.round} ラウンド：相手の入力を待っています...")
    time.sleep(2)
    data = fb_get(f"rooms/{st.session_state.room_code}")
    
    if data and data.get("hostTerm") and data.get("guestTerm"):
        st.session_state.page = "battle_view"
        st.rerun()
    else:
        st.rerun()

# --- 🌟 メイン画面：お互いの用語を大きくオープン表示 ＋ 人間審判によるポイント記録 ---
elif st.session_state.page == "battle_view":
    data = fb_get(f"rooms/{st.session_state.room_code}")
    if data:
        host_term = data.get("hostTerm", "")
        guest_term = data.get("guestTerm", "")
        host_name = data.get("host", "プレイヤー1")
        guest_name = data.get("guest", "プレイヤー2")
        
        st.subheader(f"🏆 第 {st.session_state.round} ラウンド：用語オープン！！")
        st.caption("🎙️ マイクを使ってお互いの理由説明・鑑賞バトルを行ってください！審判の判断後、下のボタンからポイントを記録します。")
        
        # 左右に大きく用語を表示
        st.markdown(f"""
        <div class='battle-container'>
            <div class='term-card'>
                <div class='term-label'>【 {host_name} の用語 】</div>
                <div class='term-title'>{host_term}</div>
            </div>
            <div class='term-card'>
                <div class='term-label'>【 {guest_name} の用語 】</div>
                <div class='term-title'>{guest_term}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("---")
        st.subheader("⚖️ 人間審判による勝者・ポイント記録パネル")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(f"👑 {host_name} の勝ち (+1)", type="primary", key=f"host_win_r{st.session_state.round}"):
                if st.session_state.is_host:
                    new_p1 = data.get("scoreP1", 0) + 1
                    fb_patch(f"rooms/{st.session_state.room_code}", {"scoreP1": new_p1})
                    st.session_state.score_p1 = new_p1
                st.session_state.page = "round_end"
                st.rerun()
        with col2:
            if st.button("🤝 引き分け (ドロー)", key=f"draw_r{st.session_state.round}"):
                st.session_state.page = "round_end"
                st.rerun()
        with col3:
            if st.button(f"👑 {guest_name} の勝ち (+1)", type="primary", key=f"guest_win_r{st.session_state.round}"):
                if st.session_state.is_host:
                    new_p2 = data.get("scoreP2", 0) + 1
                    fb_patch(f"rooms/{st.session_state.room_code}", {"scoreP2": new_p2})
                    st.session_state.score_p2 = new_p2
                st.session_state.page = "round_end"
                st.rerun()
    else:
        st.rerun()

# --- ラウンド終了・次へ ---
elif st.session_state.page == "round_end":
    data = fb_get(f"rooms/{st.session_state.room_code}")
    if data:
        st.session_state.score_p1 = data.get("scoreP1", 0)
        st.session_state.score_p2 = data.get("scoreP2", 0)
        
    st.subheader("📊 現在のトータルスコア")
    host_n = st.session_state.player_name if st.session_state.is_host else st.session_state.opponent_name
    guest_n = st.session_state.opponent_name if st.session_state.is_host else st.session_state.player_name
    st.metric(label=f"{host_n} vs {guest_n}", value=f"{st.session_state.score_p1} 勝 - {st.session_state.score_p2} 勝")
    
    st.write("---")
    if st.session_state.round < 3:
        if st.button("次ラウンドへ進む ➔", type="primary", key=f"next_round_{st.session_state.round}"):
            st.session_state.round += 1
            if st.session_state.is_host:
                fb_patch(f"rooms/{st.session_state.room_code}", {
                    "round": st.session_state.round,
                    "hostTerm": "", "guestTerm": ""
                })
            st.session_state.page = "input"
            st.rerun()
    else:
        if st.button("🎉 最終結果（表彰式）へ進む", type="primary", key="final_results_btn"):
            st.session_state.page = "final"
            st.rerun()

# --- 最終結果画面 ---
elif st.session_state.page == "final":
    st.balloons()
    st.subheader("🎉 3本勝負 最終結果発表！ 🎉")
    
    data = fb_get(f"rooms/{st.session_state.room_code}")
    if data:
        p1 = data.get("scoreP1", 0)
        p2 = data.get("scoreP2", 0)
    else:
        p1, p2 = st.session_state.score_p1, st.session_state.score_p2
        
    host_n = st.session_state.player_name if st.session_state.is_host else st.session_state.opponent_name
    guest_n = st.session_state.opponent_name if st.session_state.is_host else st.session_state.player_name
    
    if p1 > p2:
        st.header(f"👑 総合優勝：{host_n} ！！")
    elif p2 > p1:
        st.header(f"👑 総合優勝：{guest_n} ！！")
    else:
        st.header("🤝 決着つかずのドロー！")
        
    st.metric(label="最終勝利数", value=f"{host_n} [{p1}勝] - [{p2}勝] {guest_n}")
    
    st.write("---")
    if st.button("タイトルに戻る", key="back_to_menu_btn"):
        st.session_state.page = "menu"
        st.rerun()
