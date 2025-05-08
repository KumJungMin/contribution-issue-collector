import streamlit as st
import requests
import streamlit.components.v1 as components

def fetch_issues(repo, pages=2, per_page=15, token=None):
    issues = []
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    for page in range(1, pages + 1):
        url = f"https://api.github.com/repos/{repo}/issues"
        params = {"page": page, "per_page": per_page}
        try:
            res = requests.get(url, params=params, headers=headers, timeout=10)
            res.raise_for_status()
        except requests.RequestException as e:
            st.error(f"API 요청 실패: {e}")
            return []
        for issue in res.json():
            issues.append({
                "title": issue.get("title", ""),
                "body": (issue.get("body") or "")[:500],
                "url": issue.get("html_url", "")
            })
    return issues

st.title("🛠️ GitHub 이슈 수집기 (Google AI Studio 분석용)")

repo_input = st.text_input("🔗 GitHub 저장소 (형식: owner/repo)", "vercel/next.js")
pages = st.slider("📄 페이지 수 (1페이지당 15개)", 1, 10, 3)
# token = st.text_input("🔑 GitHub Personal Access Token (선택)", type="password")  # 필요시 활성화

if st.button("이슈 수집하기"):
    with st.spinner("이슈 수집 중..."):
        issues = fetch_issues(repo_input, pages)  # token=token 도 가능

    if not issues:
        st.warning("이슈가 없거나 조건에 맞는 항목이 없습니다.")
    else:
        st.info(f"🔍 총 {len(issues)}개의 이슈가 수집되었습니다.")

        markdown_list = [
            f"""## Issue {i}
**Title**: {issue['title']}

**Body**:
{issue['body']}

**URL**: {issue['url']}
---
""" for i, issue in enumerate(issues, 1)
        ]
        markdown_text = "\n".join(markdown_list)

        prompt = f"""너는 오픈소스에 기여하려는 오픈소스 기여 경험이 많은 10년차 개발자야.

위의 이슈들을 검색해서 내용을 읽어보고 밑의 기여하기 좋은 기준에 맞게 분류해줘.
이슈들이 있는 url은 https://github.com/{repo_input}/issues 이야.

이슈를 분류할땐 이슈 내용, 원인, 해결방향과 기준에 얼마나 잘 맞는지(상,중,하), 기술적인 난이도 (상,중,하) 로 평가해줘.

[기여하기 좋은 이슈 기준]
이슈의 내용이 상세하게 잘 작성되어 있는 경우
이슈의 내용 안에 버그나 에러의 로그와 재현할 수 있는 방법이 명시되어 있는 경우
이슈 내에 의심되는 소스코드의 위치가 제보자나 메인테이너에 의해 특정된경우
메인테이너가 이슈의 내용을 확인하고 문제가 맞아서 방향을 정해주거나 기여 해달라고 한 경우
메인테이너가 직접  작성한 이슈
이슈의 라벨에 good first issue 가 달려있고, blocked 나 wait-for-triage가 없는 이슈
이슈를 해결하는 PR이 아직 생성되지 않은 이슈 (누군가가 PR을 만들겠다고만 말하고 PR이 아직 생성 안된건 상관 없음)

위의 기준에 잘 맞는 이슈일수록 상세하게 설명하고 강조해줘.
위의 기준에 안맞는 이슈는 요약할 필요 없어.

분석한 내용을 한눈에 볼 수 있게 표로도 정리해줘.
"""

        combined = prompt + "\n\n" + markdown_text

        st.success("✅ 아래 내용을 복사하여 Google AI Studio에 붙여넣으세요!")
        components.html(f"""
        <textarea id="copyTarget" style="width:100%; height:400px;">{combined}</textarea>
        <button onclick="navigator.clipboard.writeText(document.getElementById('copyTarget').value)">📋 전체 복사</button>
        """, height=450)

        st.markdown("👉 [Google AI Studio 바로가기](https://aistudio.google.com/prompts/new_chat)")
