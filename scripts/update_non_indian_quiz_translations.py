#!/usr/bin/env python3
"""Deterministically update selected non-Indian locale keys for quiz control copy."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCALES_DIR = ROOT / "frontend" / "src" / "locales"

UPDATES = {
    "de": {
        "joinInformation": "Teilnahmeinformationen",
        "joinUrl": "Teilnahme-URL:",
        "copyJoinLink": "Teilnahme-Link kopieren",
        "joinCode": "Teilnahmecode",
        "enterCodeAt": "Diesen Code unter /join eingeben",
        "readyToStartFirst": "Bereit zum Start?",
        "clickAdvanceToStart": "Klicken Sie auf \"Erste Frage starten\", um den Teilnehmenden die erste Frage zu zeigen.",
        "startFirstQuestion": "Erste Frage starten",
        "presentView": "Präsentieren",
    },
    "es": {
        "joinInformation": "Información para unirse",
        "joinUrl": "URL para unirse:",
        "copyJoinLink": "Copiar enlace de acceso",
        "joinCode": "Código de acceso",
        "enterCodeAt": "Introduce este código en /join",
        "readyToStartFirst": "¿Listo para comenzar?",
        "clickAdvanceToStart": "Haz clic en \"Iniciar primera pregunta\" para mostrar la primera pregunta a los participantes.",
        "startFirstQuestion": "Iniciar primera pregunta",
        "presentView": "Presentar",
    },
    "fr": {
        "joinInformation": "Informations de participation",
        "joinUrl": "URL de participation :",
        "copyJoinLink": "Copier le lien de participation",
        "joinCode": "Code de participation",
        "enterCodeAt": "Saisissez ce code sur /join",
        "readyToStartFirst": "Prêt à commencer ?",
        "clickAdvanceToStart": "Cliquez sur \"Démarrer la première question\" pour afficher la première question aux participants.",
        "startFirstQuestion": "Démarrer la première question",
        "presentView": "Présenter",
    },
    "ru": {
        "joinInformation": "Информация для входа",
        "joinUrl": "Ссылка для входа:",
        "copyJoinLink": "Скопировать ссылку входа",
        "joinCode": "Код входа",
        "enterCodeAt": "Введите этот код на /join",
        "readyToStartFirst": "Готовы начать?",
        "clickAdvanceToStart": "Нажмите «Начать первый вопрос», чтобы показать участникам первый вопрос.",
        "startFirstQuestion": "Начать первый вопрос",
        "presentView": "Показать",
    },
}


def main() -> None:
    for locale, values in UPDATES.items():
        path = LOCALES_DIR / locale / "translation.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        quiz = data.get("quiz")
        if not isinstance(quiz, dict):
            raise ValueError(f"Missing 'quiz' object in {path}")

        quiz.update(values)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Updated {path}")


if __name__ == "__main__":
    main()
