from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union

_GSTATIC = "https://fonts.gstatic.com/s/i/short-term/release/googlesymbols"

def _rgba(hex_color: str) -> dict:
    r = int(hex_color[1:3], 16) / 255
    g = int(hex_color[3:5], 16) / 255
    b = int(hex_color[5:7], 16) / 255
    return {"red": round(r, 4), "green": round(g, 4), "blue": round(b, 4), "alpha": 1}

def _esc_dollar(s: str) -> str:
    return s.replace("$", "&#36;")

def _nl_to_br(s: str) -> str:
    return _esc_dollar(s).replace("\n", "<br>")

def _colored(text: str, color: str, bold: bool = False) -> str:
    inner = f"<b>{text}</b>" if bold else text
    return f'<font color="{color}">{inner}</font>'


# ---------------------------------------------------------------------------
# Widgets (Flutter-like components)
# ---------------------------------------------------------------------------

class Widget:
    pass

@dataclass
class Icon:
    """Google Material Symbols icon generator."""
    name: str
    size: int = 48

    @property
    def url(self) -> str:
        return f"{_GSTATIC}/{self.name}/default/{self.size}px.svg"

@dataclass
class Chip(Widget):
    label: str
    icon: Optional[Union[Icon, str]] = None

@dataclass
class Stat(Widget):
    top: str
    value: str
    bottom: str = ""

@dataclass
class Field(Widget):
    label: str
    value: str
    icon: Optional[Union[Icon, str]] = None
    color: Optional[str] = None

@dataclass
class FieldLink(Widget):
    label: str
    value: str
    btn: str
    url: str
    icon: Optional[Union[Icon, str]] = None
    color: Optional[str] = None

@dataclass
class Code(Widget):
    text: str

@dataclass
class Image(Widget):
    url: str

class Divider(Widget):
    pass

@dataclass
class LinkButton(Widget):
    label: str
    url: str


@dataclass
class GridItem:
    title: str
    subtitle: Optional[str] = None
    image_url: Optional[str] = None


@dataclass
class Grid(Widget):
    title: Optional[str] = None
    columns: int = 2
    items: list[GridItem] = field(default_factory=list)


@dataclass
class RowItem:
    widget: Widget
    weight: int = 1


@dataclass
class Column(Widget):
    """Stack multiple supported widgets inside one Row column."""
    widgets: list[Widget]


@dataclass
class Row(Widget):
    items: list[RowItem]


@dataclass
class TextParagraph(Widget):
    text: str
    color: Optional[str] = None
    bold: bool = False


@dataclass
class DecoratedText(Widget):
    text: str
    top_label: Optional[str] = None
    bottom_label: Optional[str] = None
    start_icon: Optional[Union[Icon, str]] = None
    end_icon: Optional[Union[Icon, str]] = None


class ButtonStyle(Enum):
    FILLED = "FILLED"
    OUTLINED = "OUTLINED"
    TEXT = "BORDERLESS"


@dataclass
class Button(Widget):
    label: str
    url: str
    style: ButtonStyle = ButtonStyle.OUTLINED
    icon: Optional[Union[Icon, str]] = None


@dataclass
class ButtonGroup(Widget):
    buttons: list[Button]


# ---------------------------------------------------------------------------
# Styling & Themes (ThemeData equivalent)
# ---------------------------------------------------------------------------

@dataclass
class NotificationStyle:
    """Defines the visual theme and header configuration for the notification card."""
    subtitle: str
    icon: Union[Icon, str]
    color: str
    marker: str = ""
    field_icon: Union[Icon, str] = field(default_factory=lambda: Icon("label"))

    def resolve_icon_url(self, icon: Union[Icon, str]) -> str:
        return icon.url if isinstance(icon, Icon) else icon

class NotificationTheme:
    """Predefined styles (like Flutter's Colors or TextThemes)."""
    INFO = NotificationStyle(subtitle="情報通知", icon=Icon("info"), color="#4285F4", field_icon=Icon("label"))
    SUCCESS = NotificationStyle(subtitle="完了通知", icon=Icon("check_circle"), color="#0F9D58", marker="✓", field_icon=Icon("check"))
    WARNING = NotificationStyle(subtitle="警告", icon=Icon("warning"), color="#F4B400", marker="⚠", field_icon=Icon("priority_high"))
    ERROR = NotificationStyle(subtitle="エラー", icon=Icon("error"), color="#DB4437", marker="!", field_icon=Icon("close"))
    APPROVAL = NotificationStyle(subtitle="承認・確認待ち", icon=Icon("pending_actions"), color="#4285F4", field_icon=Icon("chevron_right"))


# ---------------------------------------------------------------------------
# Layout & Structuring
# ---------------------------------------------------------------------------

def _icon_payload(icon: Union[Icon, str]) -> dict:
    return {"materialIcon": {"name": icon.name}} if isinstance(icon, Icon) else {"iconUrl": icon}


def _button_payload(button: Button) -> dict:
    payload = {
        "text": _esc_dollar(button.label),
        "onClick": {"openLink": {"url": button.url}},
        "type": button.style.value,
    }
    if button.icon is not None:
        payload["icon"] = _icon_payload(button.icon)
    return payload


def _widget_payload(widget: Widget, style: NotificationStyle) -> dict:
    default_icon = style.resolve_icon_url(style.field_icon)

    if isinstance(widget, Field):
        icon = widget.icon.url if isinstance(widget.icon, Icon) else widget.icon or default_icon
        label = _colored(_esc_dollar(widget.label), widget.color, bold=True) if widget.color else _esc_dollar(widget.label)
        return {"decoratedText": {"startIcon": {"iconUrl": icon}, "topLabel": label, "text": _nl_to_br(widget.value), "wrapText": True}}
    if isinstance(widget, FieldLink):
        icon = widget.icon.url if isinstance(widget.icon, Icon) else widget.icon or default_icon
        label = _colored(_esc_dollar(widget.label), widget.color, bold=True) if widget.color else _esc_dollar(widget.label)
        return {"decoratedText": {"startIcon": {"iconUrl": icon}, "topLabel": label, "text": _nl_to_br(widget.value), "wrapText": True, "button": {"text": _esc_dollar(widget.btn), "onClick": {"openLink": {"url": widget.url}}, "type": "OUTLINED"}}}
    if isinstance(widget, Code):
        return {"textParagraph": {"text": f"<code>{_nl_to_br(widget.text)}</code>"}}
    if isinstance(widget, Image):
        return {"image": {"imageUrl": widget.url}}
    if isinstance(widget, Divider):
        return {"divider": {}}
    if isinstance(widget, TextParagraph):
        content = _nl_to_br(widget.text)
        if widget.color:
            content = _colored(content, widget.color, bold=widget.bold)
        elif widget.bold:
            content = f"<b>{content}</b>"
        return {"textParagraph": {"text": content}}
    if isinstance(widget, DecoratedText):
        content = {"text": _nl_to_br(widget.text), "wrapText": True}
        if widget.top_label is not None:
            content["topLabel"] = _esc_dollar(widget.top_label)
        if widget.bottom_label is not None:
            content["bottomLabel"] = _esc_dollar(widget.bottom_label)
        if widget.start_icon is not None:
            content["startIcon"] = _icon_payload(widget.start_icon)
        if widget.end_icon is not None:
            content["endIcon"] = _icon_payload(widget.end_icon)
        return {"decoratedText": content}
    if isinstance(widget, Grid):
        if widget.columns < 1 or not widget.items:
            raise ValueError("Grid requires at least one column and one item")
        grid = {"columnCount": widget.columns, "items": []}
        if widget.title is not None:
            grid["title"] = _esc_dollar(widget.title)
        for item in widget.items:
            entry = {"title": _esc_dollar(item.title)}
            if item.subtitle is not None:
                entry["subtitle"] = _esc_dollar(item.subtitle)
            if item.image_url is not None:
                entry["image"] = {"imageUri": item.image_url}
            grid["items"].append(entry)
        return {"grid": grid}
    if isinstance(widget, Row):
        if not 1 <= len(widget.items) <= 2:
            raise ValueError("Row supports one or two items")
        if any(item.weight < 1 for item in widget.items):
            raise ValueError("RowItem.weight must be positive")
        minimum_weight = min(item.weight for item in widget.items)
        columns = []
        for item in widget.items:
            children = item.widget.widgets if isinstance(item.widget, Column) else [item.widget]
            if not children:
                raise ValueError("Column requires at least one widget")
            serialized = []
            for child_widget in children:
                child = _widget_payload(child_widget, style)
                if next(iter(child)) not in {"textParagraph", "image", "decoratedText", "buttonList", "chipList"}:
                    raise ValueError(f"{type(child_widget).__name__} is not supported inside Row")
                serialized.append(child)
            size = "FILL_MINIMUM_SPACE" if item.weight == minimum_weight and any(
                other.weight > item.weight for other in widget.items
            ) else "FILL_AVAILABLE_SPACE"
            columns.append({"horizontalSizeStyle": size, "widgets": serialized})
        return {"columns": {"columnItems": columns}}
    if isinstance(widget, Button):
        return {"buttonList": {"buttons": [_button_payload(widget)]}}
    if isinstance(widget, ButtonGroup):
        if not widget.buttons:
            raise ValueError("ButtonGroup requires at least one button")
        return {"buttonList": {"buttons": [_button_payload(button) for button in widget.buttons]}}
    raise TypeError(f"Unsupported widget: {type(widget).__name__}")

@dataclass
class Section:
    header: Optional[str] = None
    collapsible: bool = False
    uncollapsible_count: int = 0
    widgets: list[Widget] = field(default_factory=list)

    def _resolve_icon(self, icon: Optional[Union[Icon, str]], default: str) -> str:
        if not icon:
            return default
        return icon.url if isinstance(icon, Icon) else icon

    def build(self, style: NotificationStyle) -> dict:
        out_widgets = []
        pending_chips = []
        pending_stats = []
        pending_buttons = []

        accent = style.color

        def flush_chips():
            if pending_chips:
                chips_data = []
                for c in pending_chips:
                    cd = {"label": _esc_dollar(c.label)}
                    if c.icon:
                        cd["icon"] = {"iconUrl": self._resolve_icon(c.icon, "")}
                    chips_data.append(cd)
                out_widgets.append({"chipList": {"chips": chips_data}})
                pending_chips.clear()

        def flush_stats():
            while pending_stats:
                batch = pending_stats[:2]
                del pending_stats[:2]
                items = [{
                    "horizontalSizeStyle": "FILL_AVAILABLE_SPACE",
                    "horizontalAlignment": "START",
                    "verticalAlignment": "CENTER",
                    "widgets": [{
                        "decoratedText": {
                            "topLabel": _esc_dollar(s.top),
                            "text": _colored(_esc_dollar(s.value), accent, bold=True),
                            "bottomLabel": _esc_dollar(s.bottom) if s.bottom else "",
                        }
                    }],
                } for s in batch]
                out_widgets.append({"columns": {"columnItems": items}})

        def flush_buttons():
            if pending_buttons:
                out_widgets.append({"divider": {}})
                out_widgets.append({"buttonList": {"buttons": [
                    {"text": _esc_dollar(b.label), "onClick": {"openLink": {"url": b.url}}, "color": _rgba(accent)}
                    for b in pending_buttons
                ]}})
                pending_buttons.clear()

        def flush_inline():
            flush_chips()
            flush_stats()

        for w in self.widgets:
            if isinstance(w, Chip):
                flush_stats()
                pending_chips.append(w)
            elif isinstance(w, Stat):
                flush_chips()
                pending_stats.append(w)
            elif isinstance(w, LinkButton):
                flush_inline()
                pending_buttons.append(w)
            else:
                flush_inline()
                out_widgets.append(_widget_payload(w, style))

        flush_inline()
        flush_buttons()

        sec_dict = {"widgets": out_widgets}
        if self.header:
            sec_dict["header"] = _colored(_esc_dollar(self.header), accent, bold=True)
        if self.collapsible:
            sec_dict["collapsible"] = True
            if self.uncollapsible_count > 0:
                sec_dict["uncollapsibleWidgetsCount"] = self.uncollapsible_count

        return sec_dict


# ---------------------------------------------------------------------------
# Notification Payload & Client
# ---------------------------------------------------------------------------

class BaseMessage:
    """Base interface for messages sent via Notifier."""
    def build_payload(self) -> dict:
        raise NotImplementedError

@dataclass
class TextMessage(BaseMessage):
    """A simple raw text message without a Card UI."""
    text: str

    def build_payload(self) -> dict:
        return {"text": _esc_dollar(self.text)}

@dataclass
class Notification(BaseMessage):
    """A structured Card message."""
    style: NotificationStyle
    title: str = ""
    message: Optional[str] = None
    footer: Optional[str] = None
    sections: list[Section] = field(default_factory=list)

    def build_payload(self) -> dict:
        built_sections = []
        first_widgets = []
        accent = self.style.color

        if self.message:
            marker = f"{_colored(self.style.marker, accent, bold=True)} " if self.style.marker else ""
            first_widgets.append({"textParagraph": {"text": marker + _nl_to_br(self.message)}})

        for s in self.sections:
            sd = s.build(self.style)
            if sd.get("widgets"):
                built_sections.append(sd)

        if first_widgets:
            if built_sections and "header" not in built_sections[0]:
                built_sections[0]["widgets"] = first_widgets + built_sections[0]["widgets"]
            else:
                built_sections.insert(0, {"widgets": first_widgets})

        if built_sections and "header" not in built_sections[0]:
            built_sections[0]["header"] = _colored(self.style.subtitle.upper(), accent, bold=True)

        if self.footer and built_sections:
            built_sections[-1]["widgets"].append({"textParagraph": {"text": _colored(_nl_to_br(self.footer), "#9AA0A6")}})

        return {
            "cardsV2": [{
                "cardId": "notify-card",
                "card": {
                    "header": {
                        "title": self.title,
                        "subtitle": self.style.subtitle,
                        "imageUrl": self.style.resolve_icon_url(self.style.icon),
                        "imageType": "CIRCLE",
                    },
                    "sections": [s for s in built_sections if s.get("widgets")],
                },
            }]
        }
