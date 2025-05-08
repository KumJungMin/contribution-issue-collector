import streamlit as st
import requests
import streamlit.components.v1 as components
import re
import time

def filter_non_bot_comments(comments_data):
    filtered = []
    for c in comments_data:
        user = c.get("user", {})
        login = user.get("login", "")
        user_type = user.get("type", "")
        if user_type == "Bot" or re.search(r'\[bot\]$', login, re.IGNORECASE):
            continue
        filtered.append(f"{login}: {c.get('body', '')}")
    return filtered

def fetch_issues_one_page(repo, page=1, per_page=10, token=None, collect_comments=True):
    issues = []
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"https://api.github.com/repos/{repo}/issues"
    params = {"page": page, "per_page": per_page, "state": "open", "sort": "created", "direction": "desc"}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
    except requests.RequestException as e:
        st.error(f"API 요청 실패: {e}")
        return []
    for issue in res.json():
        if "Development" in issue:
            continue
        issue_number = issue.get("number")
        comments = []
        if collect_comments:
            comments_url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"
            try:
                res_cmt = requests.get(comments_url, headers=headers, timeout=10)
                res_cmt.raise_for_status()
                comments = filter_non_bot_comments(res_cmt.json())
            except requests.RequestException:
                comments = []
        labels = [label['name'] for label in issue.get('labels', [])]
        issue_type = issue.get('type', 'N/A')
        issues.append({
            "title": issue.get("title", ""),
            "body": (issue.get("body") or "")[:500],
            "url": issue.get("html_url", ""),
            "comments": comments,
            "labels": labels,
            "type": issue_type
        })
    return issues

# 🧱 UI 구성
st.title("🛠️ GitHub 이슈 수집기 (Google AI Studio 분석용)")

col1, col2 = st.columns([3, 1])
with col1:
    repo_input = st.text_input("🔗 GitHub 저장소 (형식: owner/repo)", "vercel/next.js")
with col2:
    pages = st.slider("📄 페이지 수(페이지당 10개)", 1, 10, 1)


with st.expander("💡 분석 요청 횟수 늘리기 (선택 사항)"):
    st.caption("GitHub Personal Access Token을 입력하면 더 많은 API 요청이 가능합니다.")
    token = st.text_input("🔑 Access Token", type="password")
    st.markdown("""
1. [GitHub에 로그인](https://github.com)에 접속합니다.  
2. 우측 상단 프로필 → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**  
3. **Generate new token** → **Generate new token (classic)** 클릭  
4. 토큰 이름, 만료일, 권한(`repo` 권장) 선택 후 **Generate token**  
5. 생성된 토큰은 한 번만 표시되니 꼭 복사해 안전하게 보관하세요.
""")

collect_comments = st.checkbox(
    "💬 댓글 수집 여부(봇 댓글 제외)",
    value=True,
    help="댓글이 많은 경우 수집 최대 길이에 도달할 수 있어요. 이 경우 댓글 수집 여부를 OFF해주세요."
)


if st.button("🔍 분석하기"):
    issues = []
    progress_bar = st.progress(0, text="이슈 수집 준비 중...")
    status_text = st.empty()
    with st.spinner("⏳ 이슈 수집 중..."):
        for page in range(1, pages + 1):
            status_text.text(f"이슈 {pages}페이지 중 {page}페이지 수집 중...")
            page_issues = fetch_issues_one_page(
                repo_input,
                page=page,
                per_page=10,
                token=token,
                collect_comments=collect_comments
            )
            issues.extend(page_issues)
            progress_bar.progress(page / pages, text=f"{int(page/pages*100)}% 완료")
            time.sleep(0.1)  # 사용자에게 진행 상황을 보여주기 위한 짧은 딜레이

        progress_bar.progress(1.0, text="100% 완료")
        status_text.text("이슈 수집 완료!")
        time.sleep(0.3)
        progress_bar.empty()
        status_text.empty()

    if not issues:
        st.warning("이슈가 없거나 조건에 맞는 항목이 없습니다.")
    else:
        st.success(f"✅ 총 {len(issues)}개의 이슈가 수집되었습니다.")
        markdown_list = []
        for i, issue in enumerate(issues, 1):
            comments_text = "\n".join([f"- {c}" for c in issue['comments']]) if issue['comments'] else "댓글 없음"
            labels_text = ", ".join(issue['labels']) if issue['labels'] else "라벨 없음"
            issue_type = issue['type']['name'] if isinstance(issue['type'], dict) and 'name' in issue['type'] else (issue['type'] if issue['type'] else "타입 없음")
            markdown_list.append(f"""## Issue {i}
**Title**: {issue['title']}

**Type**: {issue_type}

**Labels**: {labels_text}

**Body**:
{issue['body']}

**Comments**:
{comments_text}

**URL**: {issue['url']}
---
""")
        markdown_text = "\n".join(markdown_list)

        prompt = f"""너는 오픈소스에 기여하려는 오픈소스 기여 경험이 많은 10년차 개발자야.

위의 이슈들을 검색해서 내용을 읽어보고 밑의 기여하기 좋은 기준에 맞게 분류해줘.
이슈들이 있는 url은 https://github.com/{repo_input}/issues 이야.

이슈를 분류할땐 이슈 내용, 원인, 해결방향과 기준에 얼마나 잘 맞는지(상,중,하), 기술적인 난이도 (상,중,하) 로 평가해줘.

[기여하기 좋은 이슈 기준]
이슈의 내용이 상세하게 잘 작성되어 있는 경우 
이슈의 내용 안에 버그나 에러의 로그와 재현할 수 있는 방법이 명시되어 있는 경우 
이슈 내에 의심되는 소스코드의 위치가 제보자나 메인테이너에 의해 특정된 경우 
메인테이너가 이슈의 내용을 확인하고 문제가 맞아서 방향을 정해주거나 기여 해달라고 한 경우 
메인테이너가 직접 작성한 이슈
이슈의 라벨에 good first issue 가 달려있고, blocked 나 wait-for-triage가 없는 이슈 
이슈를 해결하는 PR이 아직 생성되지 않은 이슈 (누군가가 PR을 만들겠다고만 말하고 PR이 아직 생성 안된건 상관 없음)

위의 기준에 잘 맞는 이슈일수록 상세하게 설명하고 강조해줘.
위의 기준에 안맞는 이슈는 요약할 필요 없어.

분석한 내용을 한눈에 볼 수 있게 표로도 정리해줘.
"""

        combined = prompt + "\n\n" + markdown_text
        st.caption("🎯 아래 내용을 복사하여 [Google AI Studio](https://aistudio.google.com/prompts/new_chat)에 붙여넣으세요:")
        components.html(f"""
        <textarea id="copyTarget" style="width:100%; height:400px;">{combined}</textarea>
        <button onclick="navigator.clipboard.writeText(document.getElementById('copyTarget').value)">📋 전체 복사</button>
        """, height=450)

       
        st.markdown("---")
        st.caption("📄 프롬프트 출처: [오픈소스의 판도를 바꿀 AI 기여 가이드](https://medium.com/opensource-contributors/오픈소스의-판도를-바꿀-ai로-오픈소스-기여-완벽-가이드와-프롬프트-공유-2db85bf736b8)")
        st.caption("👤 프롬프트 원작자: [injae-kim](https://github.com/injae-kim)")
