"""
Tab: News Feed — browse RSS articles for the selected ticker.
"""

import streamlit as st


def render(selected_ticker: str) -> None:
    st.header(f"News Feed — {selected_ticker}")

    if st.button("🔄 Fetch Latest News", key="fetch_news"):
        with st.spinner("Fetching news…"):
            from core.rss_fetcher import fetch_news_for_ticker

            articles = fetch_news_for_ticker(selected_ticker)

        if articles:
            for doc in articles:
                lines = doc.page_content.split("\n")
                title_line = lines[0] if lines else "Article"
                body = (
                    "\n".join(lines[1:]).strip() if len(lines) > 1 else ""
                )

                with st.container(border=True):
                    st.markdown(f"**{title_line}**")
                    if body:
                        st.write(body)

                    mc1, mc2 = st.columns(2)
                    with mc1:
                        st.caption(
                            f"📅 {doc.metadata.get('published', 'N/A')}"
                        )
                    with mc2:
                        link = doc.metadata.get("source", "")
                        if link:
                            st.caption(f"[🔗 Source]({link})")
        else:
            st.info("No articles found for this ticker.")
