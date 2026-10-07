"""Command line for the self-growing dictionary: ``rlexicon <command> ...``."""

from __future__ import annotations

import argparse

from rohingya_translate.audio import load_wav
from rohingya_translate.config import load_config
from rohingya_translate.lexicon import Entry, Lexicon, Status, meaning_from_prompt


def _image(args: argparse.Namespace):
    """The photo given with --photo, or a fresh one from the camera with --camera."""
    from rohingya_translate.images import capture_frame, load_image

    if getattr(args, "photo", None):
        return load_image(args.photo)
    if getattr(args, "camera", False):
        return capture_frame(args.camera_index)
    return None


def _warn_placeholder(lex: Lexicon) -> None:
    if lex.vision_is_placeholder:
        print("Note: these settings use a stand-in image model, not a real one. For real checks, "
              "use --config configs/models.toml")


def _describe(entry: Entry) -> str:
    s = entry.support
    spelling = f" ({entry.rohingyalish})" if entry.rohingyalish else ""
    vision = ", camera agreed" if s.vision else ""
    conflicts = f", {s.conflicts} disagree" if s.conflicts else ""
    return (f"#{entry.id} {entry.meaning}{spelling}: {entry.status.value} "
            f"[{s.speakers} speaker(s){vision}{conflicts}]")


def cmd_teach(lex: Lexicon, args: argparse.Namespace) -> None:
    if args.prompt:
        meaning, source = meaning_from_prompt(args.prompt), "prompt"
    elif args.meaning:
        meaning, source = args.meaning, "teach"
    else:
        raise SystemExit("give the meaning with --meaning, or the picture shown with --prompt")
    result = lex.teach(
        load_wav(args.audio), meaning, speaker_id=args.speaker, consent_id=args.consent,
        dialect_region=args.region, rohingyalish=args.rohingyalish, hanifi=args.hanifi,
        source=source, image=_image(args),
    )
    print(("New entry  " if result.new_entry else "Added to   ") + _describe(result.entry))
    if result.vision:
        v = result.vision
        verdict = "agrees" if v.agrees else f"does not agree (it saw: {v.top_label})"
        print(f"Camera check {verdict}, score {v.score:.2f}")
        _warn_placeholder(lex)
    for other in result.conflicts:
        print(f"Warning: sounds like {_describe(other)}")


def cmd_lookup(lex: Lexicon, args: argparse.Namespace) -> None:
    matches = lex.lookup(load_wav(args.audio), limit=args.limit)
    if not any(m.confident for m in matches):
        print("No confident match in the lexicon.")
    for m in matches:
        note = "" if m.confident else "  (weak match)"
        print(f"{m.similarity:.2f}  {_describe(m.entry)}{note}")


def cmd_see(lex: Lexicon, args: argparse.Namespace) -> None:
    image = _image(args)
    if image is None:
        raise SystemExit("give a picture with --photo, or use --camera")
    for label in lex.suggest(image, limit=args.limit):
        print(f"{label.score:.2f}  {label.text}")
    _warn_placeholder(lex)


def cmd_check(lex: Lexicon, args: argparse.Namespace) -> None:
    image = _image(args)
    if image is None:
        raise SystemExit("give a picture with --photo, or use --camera")
    v = lex.check_image(args.entry, image)
    verdict = "agrees" if v.agrees else f"does not agree (it saw: {v.top_label})"
    print(f"Camera check {verdict}, score {v.score:.2f}")
    _warn_placeholder(lex)
    print(_describe(next(e for e in lex.entries() if e.id == args.entry)))


def cmd_list(lex: Lexicon, args: argparse.Namespace) -> None:
    entries = lex.entries(Status(args.status) if args.status else None)
    if not entries:
        print("The lexicon is empty." if not args.status else f"No {args.status} entries.")
    for entry in entries:
        print(_describe(entry))


def cmd_export(lex: Lexicon, args: argparse.Namespace) -> None:
    n = lex.export_csv(args.out, Status(args.status))
    print(f"Wrote {n} clip(s) to {args.out}")


def cmd_reembed(lex: Lexicon, args: argparse.Namespace) -> None:
    print(f"Re-embedded {lex.reembed()} clip(s) with {lex.embedder_id}")


def _add_image_args(p: argparse.ArgumentParser) -> None:
    group = p.add_mutually_exclusive_group()
    group.add_argument("--photo", help="image file showing the thing")
    group.add_argument("--camera", action="store_true", help="take a photo with the webcam")
    p.add_argument("--camera-index", type=int, default=0, help="which webcam (default 0)")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rlexicon", description="Grow and query the Rohingya dictionary."
    )
    parser.add_argument("--config", help="TOML settings file (default: configs/default.toml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("teach", help="add a recording of a word and its meaning")
    p.add_argument("audio", help="WAV recording of one word or short phrase")
    p.add_argument("--meaning", help="what it means in English")
    p.add_argument("--prompt", help="picture the speaker was shown; its file name is the meaning")
    p.add_argument("--speaker", required=True, help="pseudonymous speaker ID, e.g. S014")
    p.add_argument("--consent", required=True, help="ID of the speaker's consent record")
    p.add_argument("--region", default="", help="speaker's dialect region")
    p.add_argument("--rohingyalish", default="", help="Latin spelling, if known")
    p.add_argument("--hanifi", default="", help="Hanifi Rohingya spelling, if known")
    _add_image_args(p)
    p.set_defaults(func=cmd_teach, vision_from_args=True)

    p = sub.add_parser("lookup", help="find entries that sound like a recording")
    p.add_argument("audio")
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=cmd_lookup)

    p = sub.add_parser("see", help="suggest English meanings for a photo")
    _add_image_args(p)
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=cmd_see, vision=True)

    p = sub.add_parser("check", help="check an entry's meaning against a photo")
    p.add_argument("entry", type=int, help="entry number, as shown by 'list'")
    _add_image_args(p)
    p.set_defaults(func=cmd_check, vision=True)

    p = sub.add_parser("list", help="show entries and how far they are trusted")
    p.add_argument("--status", choices=[s.value for s in Status])
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("export", help="write clips as training data (CSV)")
    p.add_argument("out", help="CSV file to write")
    p.add_argument("--status", choices=[s.value for s in Status], default=Status.VERIFIED.value)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("reembed", help="recompute vectors after changing the audio embedder")
    p.set_defaults(func=cmd_reembed)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    vision = getattr(args, "vision", False) or (
        getattr(args, "vision_from_args", False) and (args.photo or args.camera)
    )
    lex = Lexicon.open(load_config(args.config), vision=bool(vision))
    try:
        args.func(lex, args)
    finally:
        lex.close()


if __name__ == "__main__":
    main()
