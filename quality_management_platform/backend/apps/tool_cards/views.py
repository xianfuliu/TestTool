from __future__ import annotations

from apps.common.http import api_view

from .service import (
    bootstrap_from_legacy_sources,
    copy_card,
    create_card,
    create_folder,
    delete_card,
    delete_folder,
    execute_card,
    get_card_detail,
    get_folder_detail,
    list_cards_by_folder,
    list_folders,
    update_card,
    update_folder,
)


@api_view
def bootstrap(_request, payload=None):
    return bootstrap_from_legacy_sources(force=bool((payload or {}).get("force", False)))


@api_view
def overview(_request, payload=None):
    return bootstrap_from_legacy_sources(force=False)


@api_view
def folders(request, payload=None):
    if request.method == "GET":
        return list_folders()
    return create_folder(payload or {})


@api_view
def folder_detail(request, folder_id: int, payload=None):
    if request.method == "GET":
        return get_folder_detail(folder_id)
    if request.method == "PUT":
        return update_folder(folder_id, payload or {})
    return delete_folder(folder_id)


@api_view
def cards(request, payload=None):
    if request.method == "GET":
        folder_id = int((payload or {}).get("folder_id") or 0)
        if not folder_id:
            raise ValueError("folder_id 不能为空")
        return list_cards_by_folder(folder_id)
    return create_card(payload or {})


@api_view
def create_card_view(_request, payload=None):
    return create_card(payload or {})


@api_view
def card_detail(request, card_id: int, payload=None):
    if request.method == "GET":
        return get_card_detail(card_id)
    if request.method == "PUT":
        return update_card(card_id, payload or {})
    return delete_card(card_id)


@api_view
def card_copy(_request, card_id: int, payload=None):
    return copy_card(card_id)


@api_view
def card_execute(_request, card_id: int, payload=None):
    return execute_card(card_id, (payload or {}).get("variables") or {})


@api_view
def initialize_defaults(_request, payload=None):
    return bootstrap_from_legacy_sources(force=bool((payload or {}).get("force", False)))
