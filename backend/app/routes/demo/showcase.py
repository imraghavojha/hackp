from __future__ import annotations

import base64
import io
import json
import zipfile
from typing import Any
from xml.sax.saxutils import escape

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel, Field

from backend.app.demo.gmail_live import sync_recent_messages


router = APIRouter(prefix="/demo/showcase", tags=["showcase"])


class DemoActionRequest(BaseModel):
    action: str
    detail: dict[str, Any] = Field(default_factory=dict)


class DemoToolRequest(BaseModel):
    request: str


class DemoEmailRequest(BaseModel):
    from_: str | None = Field(default=None, alias="from")
    subject: str
    body: str
    received_at: str | None = None


def _decode_b64_text(value: str) -> str:
    normalized = value.strip()
    padding = (-len(normalized)) % 4
    if padding:
        normalized = f"{normalized}{'=' * padding}"
    return base64.urlsafe_b64decode(normalized.encode("utf-8")).decode("utf-8")


def _column_name(index: int) -> str:
    value = ""
    current = index + 1
    while current:
        current, remainder = divmod(current - 1, 26)
        value = chr(65 + remainder) + value
    return value


def _build_xlsx_bytes(rows: list[list[str]]) -> bytes:
    sheet_rows: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        cells: list[str] = []
        for column_index, raw_value in enumerate(row):
            cell_ref = f"{_column_name(column_index)}{row_index}"
            value = "" if raw_value is None else str(raw_value)
            if value == "":
                continue
            if value.startswith("="):
                formula = escape(value[1:])
                cells.append(f'<c r="{cell_ref}"><f>{formula}</f></c>')
            else:
                try:
                    float(value)
                    is_number = value.strip() not in {"", "nan", "NaN"}
                except ValueError:
                    is_number = False
                if is_number and not value.startswith("0"):
                    cells.append(f'<c r="{cell_ref}"><v>{escape(value)}</v></c>')
                else:
                    cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        sheet_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(sheet_rows)}</sheetData>'
        '</worksheet>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Pipeline Review" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buffer.getvalue()


@router.get("/state")
def get_state(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.load()


@router.post("/reset")
def reset_demo(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.reset()


@router.post("/observe")
def record_action(payload: DemoActionRequest, request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.record_action(payload.action, payload.detail)


@router.post("/advance-day")
def advance_day(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.advance_day()


@router.post("/excel/fast-track")
def fast_track_excel(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.fast_track_excel()


@router.post("/tool/personalize")
def personalize_tool(payload: DemoToolRequest, request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.personalize_tool(payload.request)


@router.post("/tool/generate")
def generate_tool(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.generate_tool()


@router.post("/tool/apply-pending")
def apply_pending_tool_update(request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.apply_pending_update()


@router.post("/inbox/inject")
def inject_email(payload: DemoEmailRequest, request: Request) -> dict[str, Any]:
    store = request.app.state.showcase_demo_store
    return store.inject_email(
        {
            "from": payload.from_,
            "subject": payload.subject,
            "body": payload.body,
            "received_at": payload.received_at,
        }
    )


@router.post("/inbox/sync-gmail")
def sync_gmail(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    store = request.app.state.showcase_demo_store
    result = sync_recent_messages(settings)
    if result["synced"]:
        state = store.load()
        known_ids = {message["id"] for message in state["inbox"]["messages"]}
        for message in reversed(result["messages"]):
            if message["id"] in known_ids:
                continue
            state = store.inject_email(message)
        return {"synced": True, "messages": result["messages"], "state": state}
    return result


@router.get("/download/csv")
def download_csv(
    filename: str = Query(...),
    content_b64: str = Query(...),
) -> Response:
    content = _decode_b64_text(content_b64)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=content, media_type="text/csv; charset=utf-8", headers=headers)


@router.get("/download/xlsx")
def download_xlsx(
    filename: str = Query(...),
    rows_b64: str = Query(...),
) -> Response:
    rows = json.loads(_decode_b64_text(rows_b64))
    workbook_bytes = _build_xlsx_bytes(rows)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(
        content=workbook_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
