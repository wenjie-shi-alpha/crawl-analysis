#!/usr/bin/env python3
"""Command-line helper for downloading NOAA hurricane archive pages."""

from pathlib import Path

from bs4 import BeautifulSoup

from crawling.noaa_archive_crawler import NOAAArchiveCrawler


def _display_preview(html_content: str) -> None:
    """Show a brief preview of the fetched HTML page."""
    soup = BeautifulSoup(html_content, "html.parser")

    title = soup.find("title")
    if title:
        print(f"页面标题: {title.get_text(strip=True)}")

    preview = html_content[:500]
    print("\nHTML开头内容示例:")
    print(preview + ("..." if len(html_content) > len(preview) else ""))

    links = soup.find_all("a", href=True)
    print(f"\n页面包含 {len(links)} 个链接")
    if links:
        print("\n前10个链接:")
        for idx, link in enumerate(links[:10], 1):
            link_text = link.get_text(strip=True) or "(无文本)"
            print(f"  {idx}. {link_text[:50]}: {link['href']}")


def main() -> None:
    """Download the archive index and optionally recent yearly pages."""
    print("=" * 70)
    print("NOAA飓风档案HTML获取工具")
    print("=" * 70)

    crawler = NOAAArchiveCrawler()

    try:
        html = crawler.fetch_page()
    except Exception as exc:
        print(f"✗ 请求失败: {exc}")
        return

    filepath = crawler.save_html(html)
    print(f"\n✓ HTML内容已保存到: {filepath}")
    print(f"  文件大小: {filepath.stat().st_size:,} 字节")

    print("\n" + "-" * 70)
    print("HTML内容预览")
    print("-" * 70)
    _display_preview(html)

    print("\n" + "=" * 70)
    response = input("是否要获取最近3年(2021-2023)的档案? (y/n): ").strip().lower()

    if response in {"y", "yes"}:
        years = [2021, 2022, 2023]
        saved: list[Path] = []
        for year in years:
            try:
                filepath = crawler.fetch_and_save(
                    url=f"{crawler.base_url.rstrip('/')}/{year}/",
                    filename=f"archive_{year}.html",
                    subdirectory=str(year),
                )
                print(f"✓ {year} 年档案已保存: {filepath}")
                saved.append(filepath)
            except Exception as exc:
                print(f"✗ 获取 {year} 年档案失败: {exc}")

        if saved:
            print("\n✓ 所有年份数据获取完成!")
    else:
        print("\n跳过年份数据获取")

    print(f"\n所有文件保存在: {crawler.output_dir}")


if __name__ == "__main__":
    main()
