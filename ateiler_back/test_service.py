"""Сквозной тест бекенда БЕЗ FastAPI/сети: analyze(mock) -> generate -> export."""
import asyncio, os
os.environ["STORAGE_BACKEND"] = "local"
try:
    if os.path.exists("/data/skirt/atelier.db"):
        os.remove("/data/skirt/atelier.db")
except Exception:
    pass

import db, service


async def main():
    service.ensure_db()
    sid = db.create_session()
    print("session:", sid)

    # фейковое изображение с именем, намекающим на тип (mock читает stem)
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    res = await service.analyze(sid, fake_png, "my_a_line_skirt.png")
    print(f"analyze -> type={res.skirt_type} conf={res.confidence} hint={res.length_hint_cm}cm")
    assert res.skirt_type == "a_line"

    # проверяем, что generate берёт тип из анализа
    gen = service.generate(sid, waist_cm=70, hip_cm=98, length_cm=70)
    print(f"generate -> job={gen.job_id[:8]} type={gen.skirt_type} "
          f"pieces={gen.pieces} A4={gen.pages_a4}")
    try:
        import reportlab
        has_reportlab = True
    except ImportError:
        has_reportlab = False

    assert gen.skirt_type == "a_line"
    assert gen.svg_url
    if has_reportlab:
        assert gen.pdf_url

    # файлы реально лежат в хранилище
    from storage import LocalStorage
    st = LocalStorage()
    import glob
    # Resolve the directory correctly on Windows/Unix
    storage_root = str(st.root)
    svgs = glob.glob(os.path.join(storage_root, "patterns/**/*.svg"), recursive=True)
    pdfs = glob.glob(os.path.join(storage_root, "patterns/**/*.pdf"), recursive=True)
    print(f"хранилище: {len(svgs)} svg, {len(pdfs)} pdf")
    assert svgs
    if has_reportlab:
        assert pdfs

    # export links
    if has_reportlab:
        links = service.export_links(gen.job_id, "pdf")
        print("export ->", links["download_url"])

    # override типа (fallback ручной выбор)
    gen2 = service.generate(sid, 68, 96, 60, skirt_type_override="full_circle")
    print(f"override -> type={gen2.skirt_type} A4={gen2.pages_a4}")
    assert gen2.skirt_type == "full_circle"

    # Проверка построения с карманами
    gen3 = service.generate(sid, 70, 98, 70, pocket_type="cargo")
    print(f"pockets -> pieces={gen3.pieces}")
    assert "pocket_cargo_face" in gen3.pieces

    print("\n✓ сквозной пайплайн analyze->generate->export работает")


if __name__ == "__main__":
    asyncio.run(main())
