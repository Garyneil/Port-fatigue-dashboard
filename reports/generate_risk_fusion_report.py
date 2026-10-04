from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "港口操作员多模态疲劳综合风险融合框架报告.pdf"

NAVY = colors.HexColor("#071522")
CYAN = colors.HexColor("#0F8B8D")
CYAN_LIGHT = colors.HexColor("#E9F6F6")
BLUE = colors.HexColor("#2563A6")
BLUE_LIGHT = colors.HexColor("#EAF2FA")
AMBER = colors.HexColor("#C47A12")
AMBER_LIGHT = colors.HexColor("#FFF4DD")
RED = colors.HexColor("#B83A42")
RED_LIGHT = colors.HexColor("#FCECEF")
GREEN = colors.HexColor("#287A57")
GREY_1 = colors.HexColor("#334155")
GREY_2 = colors.HexColor("#64748B")
GREY_3 = colors.HexColor("#D9E2E8")
GREY_4 = colors.HexColor("#F5F8FA")
WHITE = colors.white


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("YaHei", r"C:\Windows\Fonts\msyh.ttc", subfontIndex=0))
    pdfmetrics.registerFont(TTFont("YaHei-Bold", r"C:\Windows\Fonts\msyhbd.ttc", subfontIndex=0))
    pdfmetrics.registerFont(TTFont("YaHei-Light", r"C:\Windows\Fonts\msyhl.ttc", subfontIndex=0))
    addMapping("YaHei", 0, 0, "YaHei")
    addMapping("YaHei", 1, 0, "YaHei-Bold")


class ArchitectureDiagram(Flowable):
    """Four-stage schematic for the six-factor, quality-gated risk model."""

    def __init__(self, width: float = 174 * mm, height: float = 91 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, avail_width, avail_height):
        return min(self.width, avail_width), self.height

    def draw_box(self, c, x, y, w, h, fill, accent, title, factors, badge=None):
        c.setFillColor(fill)
        c.setStrokeColor(accent)
        c.setLineWidth(0.8)
        c.roundRect(x, y, w, h, 5, fill=1, stroke=1)
        c.setFillColor(accent)
        c.roundRect(x, y + h - 6, w, 6, 5, fill=1, stroke=0)
        c.setFillColor(NAVY)
        c.setFont("YaHei-Bold", 8.6)
        c.drawString(x + 4 * mm, y + h - 13, title)
        if badge:
            badge_w = c.stringWidth(badge, "YaHei", 5.8) + 4 * mm
            c.setFillColor(WHITE)
            c.setStrokeColor(accent)
            c.roundRect(x + w - badge_w - 3 * mm, y + h - 17, badge_w, 8, 3, fill=1, stroke=1)
            c.setFillColor(accent)
            c.setFont("YaHei", 5.8)
            c.drawCentredString(x + w - badge_w / 2 - 3 * mm, y + h - 14.5, badge)
        chip_h = 8 * mm
        chip_gap = 2.2 * mm
        chip_w = (w - 10 * mm - chip_gap) / 2
        chip_y = y + 4 * mm
        for idx, (symbol, label) in enumerate(factors):
            chip_x = x + 5 * mm + idx * (chip_w + chip_gap)
            c.setFillColor(WHITE)
            c.setStrokeColor(GREY_3)
            c.roundRect(chip_x, chip_y, chip_w, chip_h, 3, fill=1, stroke=1)
            c.setFillColor(accent)
            c.setFont("YaHei-Bold", 6.8)
            c.drawCentredString(chip_x + chip_w / 2, chip_y + 5.2 * mm, symbol)
            c.setFillColor(GREY_2)
            c.setFont("YaHei", 5.8)
            c.drawCentredString(chip_x + chip_w / 2, chip_y + 2 * mm, label)

    def arrow(self, c, x1, y1, x2, y2, color=CYAN):
        c.setStrokeColor(color)
        c.setFillColor(color)
        c.setLineWidth(1.25)
        c.line(x1, y1, x2, y2)
        if abs(y2 - y1) >= abs(x2 - x1):
            direction = 1 if y2 > y1 else -1
            c.line(x2, y2, x2 - 2.6, y2 - direction * 4)
            c.line(x2, y2, x2 + 2.6, y2 - direction * 4)
        else:
            direction = 1 if x2 > x1 else -1
            c.line(x2, y2, x2 - direction * 4, y2 - 2.6)
            c.line(x2, y2, x2 - direction * 4, y2 + 2.6)

    def stage_label(self, c, number, label, y):
        c.setFillColor(NAVY)
        c.circle(7 * mm, y, 3.2 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("YaHei-Bold", 6.5)
        c.drawCentredString(7 * mm, y - 2.1, number)
        c.setFillColor(GREY_1)
        c.setFont("YaHei-Bold", 7)
        c.drawString(12 * mm, y - 2.2, label)

    def draw(self):
        c = self.canv
        w = self.width
        h = self.height
        c.setFillColor(colors.HexColor("#F7F9FB"))
        c.setStrokeColor(GREY_3)
        c.setLineWidth(0.6)
        c.roundRect(0, 0, w, h, 7, fill=1, stroke=1)

        # Stage 1 — six factors grouped by sensing source.
        self.stage_label(c, "01", "六因子证据输入", h - 7 * mm)
        gap = 4 * mm
        bw = (w - 4 * gap) / 3
        bh = 21 * mm
        box_y = h - 32 * mm
        x1, x2, x3 = gap, 2 * gap + bw, 3 * gap + 2 * bw
        self.draw_box(c, x1, box_y, bw, bh, BLUE_LIGHT, BLUE, "EEG 神经状态",
                      [("D_EEG", "疲劳偏离程度"), ("V_Riemann", "风险域移动速度")])
        self.draw_box(c, x2, box_y, bw, bh, CYAN_LIGHT, CYAN, "摄像头 · 眼部行为",
                      [("P_PERCLOS", "单位时间闭眼率"), ("T_closure", "连续闭眼时长")], "可选模态")
        self.draw_box(c, x3, box_y, bw, bh, AMBER_LIGHT, AMBER, "任务绩效与情境",
                      [("L_anomaly", "异常感知下降"), ("C_task", "任务危险等级")])

        gate_y = h - 49 * mm
        for center in (x1 + bw / 2, x2 + bw / 2, x3 + bw / 2):
            self.arrow(c, center, box_y - 1, center, gate_y + 10 * mm)

        # Stage 2 — explicit modality gating and weight normalization.
        self.stage_label(c, "02", "证据门控与动态权重", gate_y + 6 * mm)
        gate_x = 44 * mm
        gate_w = w - 49 * mm
        gate_h = 12 * mm
        c.setFillColor(WHITE)
        c.setStrokeColor(CYAN)
        c.roundRect(gate_x, gate_y - 2 * mm, gate_w, gate_h, 5, fill=1, stroke=1)
        labels = [("可用性 a_i", "设备是否在线"), ("质量 q_i", "信号是否可信"), ("有效权重 w~_i", "缺失模态自动重归一")]
        seg_w = gate_w / 3
        for idx, (title, sub) in enumerate(labels):
            cx = gate_x + (idx + .5) * seg_w
            if idx:
                c.setStrokeColor(GREY_3)
                c.line(gate_x + idx * seg_w, gate_y, gate_x + idx * seg_w, gate_y + 6 * mm)
            c.setFillColor(NAVY)
            c.setFont("YaHei-Bold", 7.2)
            c.drawCentredString(cx, gate_y + 5.2 * mm, title)
            c.setFillColor(GREY_2)
            c.setFont("YaHei", 5.7)
            c.drawCentredString(cx, gate_y + 1.8 * mm, sub)

        # Camera-off route is shown rather than buried in the caption.
        note_y = gate_y - 7 * mm
        c.setFillColor(CYAN_LIGHT)
        c.setStrokeColor(CYAN)
        c.roundRect(gate_x, note_y, gate_w, 5 * mm, 3, fill=1, stroke=1)
        c.setFillColor(CYAN)
        c.setFont("YaHei-Bold", 6.1)
        c.drawCentredString(gate_x + gate_w / 2, note_y + 1.8 * mm,
                            "摄像头不可用 → P_PERCLOS、T_closure 权重置零 → 其余证据权重重新归一化")

        fusion_y = 22 * mm
        self.arrow(c, w / 2, note_y - 1, w / 2, fusion_y + 14 * mm)

        # Stage 3 — normalized fusion equation.
        self.stage_label(c, "03", "质量感知融合", fusion_y + 9 * mm)
        formula_x, formula_w, formula_h = 44 * mm, w - 49 * mm, 13 * mm
        c.setFillColor(NAVY)
        c.setStrokeColor(NAVY)
        c.roundRect(formula_x, fusion_y, formula_w, formula_h, 5, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont("YaHei-Bold", 8)
        c.drawCentredString(formula_x + formula_w / 2, fusion_y + 7.5 * mm,
                            "R(t) = 100 × Σ[a_i q_i w_i z_i] / Σ[a_i q_i w_i]")
        c.setFont("YaHei", 5.8)
        c.drawCentredString(formula_x + formula_w / 2, fusion_y + 3 * mm,
                            "仅对当前可用且质量合格的证据求和")

        # Stage 4 — operational outputs.
        out_y = 3.5 * mm
        self.arrow(c, w / 2, fusion_y - 1, w / 2, out_y + 10 * mm)
        self.stage_label(c, "04", "风险决策输出", out_y + 6 * mm)
        out_x, out_w = 44 * mm, w - 49 * mm
        items = [("风险值 0–100", BLUE), ("低 / 中 / 高风险", AMBER), ("置信度或拒判", RED), ("观察 / 复核 / 交班", GREEN)]
        item_gap = 2 * mm
        item_w = (out_w - 3 * item_gap) / 4
        for idx, (label, accent) in enumerate(items):
            ix = out_x + idx * (item_w + item_gap)
            c.setFillColor(WHITE)
            c.setStrokeColor(accent)
            c.roundRect(ix, out_y, item_w, 8 * mm, 3, fill=1, stroke=1)
            c.setFillColor(accent)
            c.setFont("YaHei-Bold", 6.2)
            c.drawCentredString(ix + item_w / 2, out_y + 3 * mm, label)


class AvailabilityDiagram(Flowable):
    def __init__(self, width: float = 174 * mm, height: float = 48 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def wrap(self, avail_width, avail_height):
        return min(self.width, avail_width), self.height

    def draw(self):
        c = self.canv
        w = self.width
        c.setFillColor(GREY_4)
        c.roundRect(0, 0, w, self.height, 5, fill=1, stroke=0)
        col = (w - 18 * mm) / 3
        x_positions = [5 * mm, 9 * mm + col, 13 * mm + 2 * col]
        titles = ["设备与信号检查", "动态权重重归一化", "决策输出"]
        texts = [
            "摄像头在线？|人脸/眼睛可见？|EEG质量达标？",
            "不可用模态权重置零|剩余权重自动归一|保留来源与时间戳",
            "风险等级 + 置信度|证据不足时拒判|触发复核或重新校准",
        ]
        fills = [BLUE_LIGHT, CYAN_LIGHT, AMBER_LIGHT]
        for x, title, text_lines, fill in zip(x_positions, titles, texts, fills):
            c.setFillColor(fill)
            c.setStrokeColor(GREY_3)
            c.roundRect(x, 8 * mm, col, 31 * mm, 4, fill=1, stroke=1)
            c.setFillColor(NAVY)
            c.setFont("YaHei-Bold", 8)
            c.drawCentredString(x + col / 2, 31 * mm, title)
            c.setFillColor(GREY_2)
            c.setFont("YaHei", 6.5)
            for idx, line in enumerate(text_lines.split("|")):
                c.drawCentredString(x + col / 2, 23 * mm - idx * 8, line)
        c.setStrokeColor(CYAN)
        c.setLineWidth(1.1)
        for x in [x_positions[0] + col, x_positions[1] + col]:
            c.line(x + 1.5 * mm, 23.5 * mm, x + 6 * mm, 23.5 * mm)
            c.line(x + 6 * mm, 23.5 * mm, x + 4.3 * mm, 25 * mm)
            c.line(x + 6 * mm, 23.5 * mm, x + 4.3 * mm, 22 * mm)


def build_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleCN", fontName="YaHei-Bold", fontSize=24, leading=34, textColor=NAVY, alignment=TA_LEFT, spaceAfter=8),
        "subtitle": ParagraphStyle("SubtitleCN", fontName="YaHei", fontSize=12, leading=20, textColor=CYAN, alignment=TA_LEFT),
        "meta": ParagraphStyle("Meta", fontName="YaHei", fontSize=8.5, leading=14, textColor=GREY_2),
        "h1": ParagraphStyle("H1", fontName="YaHei-Bold", fontSize=15, leading=22, textColor=NAVY, spaceBefore=10, spaceAfter=7, keepWithNext=True),
        "h2": ParagraphStyle("H2", fontName="YaHei-Bold", fontSize=11.5, leading=18, textColor=BLUE, spaceBefore=8, spaceAfter=5, keepWithNext=True),
        "body": ParagraphStyle("Body", fontName="YaHei", fontSize=9.2, leading=16, textColor=GREY_1, alignment=TA_LEFT, spaceAfter=6),
        "small": ParagraphStyle("Small", fontName="YaHei", fontSize=7.6, leading=12, textColor=GREY_2, alignment=TA_JUSTIFY),
        "caption": ParagraphStyle("Caption", fontName="YaHei", fontSize=7.5, leading=12, textColor=GREY_2, alignment=TA_CENTER, spaceBefore=3, spaceAfter=6),
        "callout": ParagraphStyle("Callout", fontName="YaHei", fontSize=9.2, leading=16, textColor=NAVY, leftIndent=9, rightIndent=9, spaceBefore=4, spaceAfter=4),
        "equation": ParagraphStyle("Equation", fontName="YaHei", fontSize=10.5, leading=18, textColor=NAVY, alignment=TA_CENTER, spaceBefore=5, spaceAfter=5),
        "bullet": ParagraphStyle("Bullet", fontName="YaHei", fontSize=9, leading=15, textColor=GREY_1, leftIndent=12, firstLineIndent=-8, bulletIndent=0, spaceAfter=3),
        "ref": ParagraphStyle("Ref", fontName="YaHei", fontSize=7.4, leading=11.5, textColor=GREY_1, leftIndent=12, firstLineIndent=-12, spaceAfter=4),
        "toc": ParagraphStyle("TOC", fontName="YaHei", fontSize=9.3, leading=17, textColor=GREY_1),
    }


def P(text, style, **kwargs):
    return Paragraph(text, style, **kwargs)


def callout(text, styles, color=CYAN_LIGHT):
    table = Table([[P(text, styles["callout"])]], colWidths=[174 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("BOX", (0, 0), (-1, -1), 0.8, CYAN),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def academic_table(data, widths, styles, header=True, font_size=7.5):
    converted = []
    for row_idx, row in enumerate(data):
        style = ParagraphStyle(
            f"Cell{row_idx}",
            parent=styles["small"],
            fontName="YaHei-Bold" if header and row_idx == 0 else "YaHei",
            fontSize=font_size,
            leading=font_size + 4,
            textColor=WHITE if header and row_idx == 0 else GREY_1,
            alignment=TA_LEFT,
        )
        converted.append([P(str(cell), style) for cell in row])
    table = Table(converted, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, GREY_3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, GREY_4]),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    table.setStyle(TableStyle(commands))
    return table


def draw_page(canvas, doc):
    canvas.saveState()
    page = canvas.getPageNumber()
    width, height = A4
    canvas.setStrokeColor(GREY_3)
    canvas.setLineWidth(.5)
    canvas.line(18 * mm, height - 15 * mm, width - 18 * mm, height - 15 * mm)
    canvas.setFont("YaHei", 7)
    canvas.setFillColor(GREY_2)
    canvas.drawString(18 * mm, height - 11.5 * mm, "PORT COGNITIVE SAFETY · METHOD REPORT")
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"{page:02d}")
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.restoreState()


def build_report():
    register_fonts()
    styles = build_styles()
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=21 * mm,
        bottomMargin=19 * mm,
        title="基于动态黎曼证据与可选PERCLOS的港口操作员综合疲劳风险融合框架",
        author="Port Fatigue Dashboard Research Prototype",
        subject="港口远程操控员疲劳与异常感知联合评估方法报告",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    doc.addPageTemplates([PageTemplate(id="report", frames=frame, onPage=draw_page)])

    story = []
    story += [
        Spacer(1, 23 * mm),
        P("基于动态黎曼证据与可选 PERCLOS 的<br/>港口操作员综合疲劳风险融合框架", styles["title"]),
        Spacer(1, 4 * mm),
        P("方法设计、风险计算、缺失模态处理与验证方案", styles["subtitle"]),
        Spacer(1, 13 * mm),
        callout("<b>核心主张</b><br/>将当前单一 EEG 疲劳概率升级为六因子时变风险函数，并通过“模态可用性 × 数据质量 × 基础权重”控制各证据是否进入融合。当操作员摄像头不可用或图像质量不足时，PERCLOS 与连续闭眼证据自动退出计算，其权重由其余有效证据重归一化承担；当总体证据不足时，系统拒绝给出确定性结论。", styles),
        Spacer(1, 15 * mm),
        P("研究原型版本 1.0", styles["meta"]),
        P("生成日期：2026年10月4日", styles["meta"]),
        P("适用对象：港口远程岸桥、场桥及集中控制席位的认知安全监测研究", styles["meta"]),
        Spacer(1, 27 * mm),
        P("重要边界", styles["h2"]),
        P("本报告提出的是待验证的方法框架。当前仓库已实现基于 SEED-VIG 的“黎曼对齐 + 切空间逻辑回归”研究基线及前端仿真，但尚未完成港口操作员现场数据采集、PERCLOS视觉算法接入、六因子权重学习和前瞻性安全验证。报告中的初始权重与风险阈值仅用于工程启动，不构成生产安全标准。", styles["body"]),
        PageBreak(),
    ]

    story += [
        P("执行摘要", styles["h1"]),
        P("远程港口作业要求操作员持续监视多个视频画面并及时发现低频但高后果的异常事件。单一脑电分类器能够提供内部神经状态证据，却难以单独区分短时注意波动、视觉行为变化与任务风险上升。反之，PERCLOS 能捕捉缓慢闭眼行为，但易受摄像头缺失、遮挡、眼镜反光、姿态偏转和照明变化影响。因此，本报告提出一个面向设备异构性的多模态风险融合框架：以黎曼脑电证据为底座，以 PERCLOS 和连续闭眼时长作为可选视觉证据，以异常感知能力下降与当前任务危险等级提供行为和情境约束。", styles["body"]),
        P("该框架以六个标准化证据构成时变综合风险 R(t)：脑状态接近疲劳原型的程度 D<sub>EEG</sub>、脑状态向高风险域移动的速度 V<sub>Riemann</sub>、单位时间闭眼比例 P<sub>PERCLOS</sub>、连续闭眼时长 T<sub>closure</sub>、异常感知能力下降 L<sub>anomaly</sub> 以及任务危险等级 C<sub>task</sub>。每项证据同时受可用性指示 a<sub>i</sub> 与数据质量 q<sub>i</sub> 调节，从而使系统能够在不同设备条件下退化运行，而不是把缺失值误当作正常值。", styles["body"]),
        P("与固定特征拼接不同，本方案强调三点：第一，EEG 风险被表示为黎曼流形上的动态轨迹而非孤立分类结果；第二，视觉模态缺失时执行显式权重重归一化，并保留决策所依据的有效证据；第三，风险输出同时包含等级、置信度和拒判状态。由此，系统能够回答“为什么预警、哪些证据有效、缺少什么信息以及是否足以作出决策”。", styles["body"]),
        Spacer(1, 4 * mm),
        P("建议交付目标", styles["h2"]),
        academic_table([
            ["阶段", "核心交付", "完成判据"],
            ["研究基线", "EEG 黎曼对齐、切空间分类与因果在线校准", "严格留一被试和短时基线评估，不使用目标被试未来窗口"],
            ["多模态原型", "操作员摄像头、PERCLOS、连续闭眼与质量门控", "摄像头断开、遮挡和低照度条件下可自动退出融合"],
            ["港口验证", "疲劳、异常感知与任务风险联合评估", "报告误报/小时、漏报率、提前量、校准误差及拒判覆盖率"],
            ["闭环决策", "持续观察、人工复核、交班准备与证据不足", "所有建议可追溯到具体模态、时间窗和质量评分"],
        ], [25*mm, 78*mm, 71*mm], styles, font_size=7.3),
        PageBreak(),
    ]

    story += [
        P("1 研究背景与问题定义", styles["h1"]),
        P("港口集中控制系统正在把传统现场操作转化为长时间、多屏幕、低身体活动但高认知负荷的远程监控任务。操作员不仅需要保持警觉，还要在设备运动、视频切换和低频异常之间迅速识别关键事件。因而，项目目标不应局限于判断“是否困倦”，而应评估疲劳是否正在削弱异常感知能力，并结合当前作业危险程度决定是否需要干预。", styles["body"]),
        P("当前研究原型使用 17 通道、3 秒 EEG 窗口，计算收缩协方差矩阵，经受试者级黎曼对齐后映射至单位点切空间，再由标准化逻辑回归输出困倦概率。模型在 12 名 SEED-VIG 受试者、4,566 个平衡样本上的离线留一被试评估获得 0.891±0.053 的平均平衡准确率。然而，该结果使用目标被试整批无标签窗口估计对齐中心，属于传导式离线估计，不能代表港口现场的因果在线性能。", styles["body"]),
        P("PERCLOS 是给定时间窗内眼睑至少闭合约 80% 的时间比例，经典实现常采用一分钟窗口。其优势是非接触、可直观解释，并能反映缓慢闭眼而非普通眨眼；其局限是依赖摄像头视角、图像质量和面部可见性，且在中度困倦、特定年龄或航空任务中可能不敏感。因此，PERCLOS 应作为条件性证据，而不是必需输入或唯一真值。", styles["body"]),
        P("问题可形式化为：给定 EEG 窗口、可选眼部视频、异常事件响应记录和作业情境，在每个更新时间 t 输出风险值 R(t)、风险等级 y(t)、置信度 Q(t) 和拒判标志 A(t)，同时记录每项证据是否可用及其贡献。", styles["body"]),
        Spacer(1, 3 * mm),
        callout("<b>方法边界：</b>风险评估用于辅助认知安全监测和人工复核，不直接替代岗位安全规程、医学诊断或强制交班决定。", styles, AMBER_LIGHT),
        P("2 相关技术与差异化定位", styles["h1"]),
        P("明东团队的代表性工作覆盖脑疲劳神经机制、脑力负荷、自适应人机协作以及脑与解码器共同演进；李远清团队的代表性工作覆盖跨被试领域泛化、协方差对齐、多模态 EEG/EOG 驾驶警觉度估计和可穿戴实时注意调节。由此，“跨被试”“协方差对齐”或“EEG 与眼部指标融合”本身均不宜被表述为本项目的独立原创点。", styles["body"]),
        academic_table([
            ["方向", "已有代表性能力", "本项目的差异化焦点"],
            ["脑疲劳与人机协作", "脑网络、脑力负荷、自适应自动化、脑机共同学习", "面向港口作业危险度的证据化预警与交班辅助，而非通用脑机控制"],
            ["跨被试与多模态解码", "领域泛化、协方差对齐、EEG/EOG融合、可穿戴注意反馈", "动态黎曼轨迹、可选PERCLOS、质量门控、缺失模态重归一化和安全拒判"],
            ["当前研究原型", "RA + Tangent-LR，可解释且轻量", "从静态困倦概率扩展为疲劳—异常感知—任务风险联合决策"],
        ], [35*mm, 67*mm, 72*mm], styles, font_size=7.2),
        PageBreak(),
    ]

    story += [
        P("3 总体融合框架", styles["h1"]),
        P("总体框架包含神经证据、眼部行为证据、任务绩效与情境证据三条输入链，并在融合前执行可用性和质量判断。系统每两秒更新一次风险，但各证据可以使用不同长度的回顾窗口：EEG 保持短窗快速响应，PERCLOS 使用较长窗口抑制偶发眨眼影响，异常感知指标在事件发生后更新，任务危险等级由业务系统实时提供。", styles["body"]),
        ArchitectureDiagram(),
        P("图1｜六因子综合风险融合框架。PERCLOS 与连续闭眼证据属于可选视觉模态；缺失或低质量时不进入风险计算。", styles["caption"]),
        P("3.1 神经证据链", styles["h2"]),
        P("对第 t 个 EEG 窗口 X(t) 计算收缩协方差矩阵 C(t)。以个人清醒基线的黎曼中心 C<sub>ref</sub> 为参考，对协方差进行对齐并计算仿射不变黎曼距离 d<sub>R</sub>(C(t), C<sub>ref</sub>)。D<sub>EEG</sub>(t) 表示经个人基线分位数标准化后的偏离程度，V<sub>Riemann</sub>(t) 表示偏离度的正向变化速度。前者回答“距离疲劳风险域有多远”，后者回答“正在以多快速度接近风险域”。", styles["body"]),
        P("3.2 眼部行为证据链", styles["h2"]),
        P("操作员摄像头首先执行人脸可见性、眼部关键点置信度、遮挡、头部姿态和照度检查。仅当视觉质量 q<sub>vision</sub> 达标时，系统才计算 P<sub>PERCLOS</sub>(t) 与 T<sub>closure</sub>(t)。PERCLOS 建议以 60 秒滑动窗口为初始实现，每 2 秒更新；连续闭眼时长作为快速危险事件单独保留，避免长窗口平均掩盖短时微睡眠。具体窗口和闭合阈值必须使用港口数据重新标定。", styles["body"]),
        P("3.3 异常感知与任务情境", styles["h2"]),
        P("L<sub>anomaly</sub>(t) 由异常目标漏检、反应时间延长和误操作等指标相对个人清醒基线的变化构成。C<sub>task</sub>(t) 则描述当前作业后果，例如设备高速运动、吊具临近人员或车辆、危险品作业以及多目标冲突。两者使相同的生理疲劳证据在不同作业情境下产生不同的干预优先级。", styles["body"]),
        PageBreak(),
    ]

    story += [
        P("4 综合风险计算方法", styles["h1"]),
        P("4.1 六因子基础风险", styles["h2"]),
        callout("<b>基础表达</b><br/><br/>R<sub>base</sub>(t) = w<sub>1</sub>D<sub>EEG</sub>(t) + w<sub>2</sub>V<sub>Riemann</sub>(t) + w<sub>3</sub>P<sub>PERCLOS</sub>(t) + w<sub>4</sub>T<sub>closure</sub>(t) + w<sub>5</sub>L<sub>anomaly</sub>(t) + w<sub>6</sub>C<sub>task</sub>(t)", styles),
        Spacer(1, 4 * mm),
        academic_table([
            ["符号", "含义", "建议标准化方式", "初始基础权重"],
            ["D<sub>EEG</sub>", "脑状态接近疲劳原型的程度", "个人清醒基线分位数或稳健Z分数后截断至[0,1]", "0.25"],
            ["V<sub>Riemann</sub>", "脑状态向高风险域移动的速度", "黎曼距离正向差分，经指数平滑后缩放至[0,1]", "0.15"],
            ["P<sub>PERCLOS</sub>", "单位时间内高度闭眼比例", "60秒滑窗比例；闭合判据和阈值由现场标定", "0.20"],
            ["T<sub>closure</sub>", "连续闭眼事件严重度", "按连续时长的分段或饱和函数缩放", "0.10"],
            ["L<sub>anomaly</sub>", "异常感知能力下降", "反应时间、漏检率和误操作相对个人基线的组合", "0.20"],
            ["C<sub>task</sub>", "当前任务危险等级", "由业务规则映射为[0,1]，并记录规则来源", "0.10"],
        ], [22*mm, 54*mm, 72*mm, 26*mm], styles, font_size=6.9),
        P("表1｜建议的工程启动权重。它们是待学习和待标定的先验，不是已经验证的最优参数。", styles["caption"]),
        P("4.2 模态可用性与质量加权", styles["h2"]),
        P("固定加权在摄像头缺失时会产生系统性偏差：若把缺失 PERCLOS 填为零，会被误解为眼睛始终睁开；若保留原权重，则风险值被人为压低。为此，定义 a<sub>i</sub>(t)∈{0,1} 表示第 i 项证据是否可用，q<sub>i</sub>(t)∈[0,1] 表示其数据质量。最终风险为：", styles["body"]),
        callout("<b>可部署表达</b><br/><br/>R(t) = 100 × [Σ<sub>i=1…6</sub> a<sub>i</sub>(t) q<sub>i</sub>(t) w<sub>i</sub> z<sub>i</sub>(t)] / [Σ<sub>i=1…6</sub> a<sub>i</sub>(t) q<sub>i</sub>(t) w<sub>i</sub>]<br/><br/>其中 z<sub>i</sub>(t) 为标准化后的六类证据。若分母低于最低有效证据阈值，系统输出“证据不足”，不输出确定性风险等级。", styles, BLUE_LIGHT),
        Spacer(1, 4 * mm),
        AvailabilityDiagram(),
        P("图2｜设备异构和信号质量变化下的安全降级机制。", styles["caption"]),
        P("当操作员摄像头关闭、被遮挡或眼部识别置信度不足时，a<sub>PERCLOS</sub>=a<sub>closure</sub>=0，两个视觉权重退出分子与分母。系统继续依靠 EEG、异常感知与任务危险度工作，并在界面显示“PERCLOS 未启用，不参与评估”。摄像头恢复后需经过连续质量确认再重新加入，避免频繁开关造成风险跳变。", styles["body"]),
        PageBreak(),
    ]

    story += [
        P("5 时序平滑、风险分层与安全拒判", styles["h1"]),
        P("瞬时风险易受脑电伪迹、眨眼和单次事件波动影响。系统应先对 R(t) 进行指数加权移动平均，得到 E(t)=λE(t−1)+(1−λ)R(t)，再结合进入阈值、退出阈值和持续时间形成迟滞决策。λ、时间窗及阈值均应在港口数据上选择，以误报/小时和严重疲劳漏报率为主要约束。", styles["body"]),
        academic_table([
            ["输出状态", "初始演示区间", "决策含义", "推荐动作"],
            ["正常", "E(t) < 40", "有效证据支持状态稳定", "常规监测"],
            ["观察", "40 ≤ E(t) < 65", "出现轻度或不一致风险信号", "继续观察并检查信号质量"],
            ["预警", "65 ≤ E(t) < 80 且持续", "多项证据支持疲劳风险上升", "人工复核、提醒与任务降载"],
            ["高风险", "E(t) ≥ 80 且持续，或出现严重闭眼事件", "认知安全风险可能影响作业", "准备交班或执行既定干预流程"],
            ["证据不足", "有效权重或置信度低于要求", "系统无法可靠判断", "重新校准、恢复设备或人工接管评估"],
        ], [26*mm, 38*mm, 60*mm, 50*mm], styles, font_size=7.1),
        P("表2｜用于原型演示的风险等级。数值不是港口生产标准，需经任务数据和安全部门共同标定。", styles["caption"]),
        P("拒判不是系统失败，而是安全功能。建议同时计算融合置信度 Q(t)，其输入包括有效权重覆盖率、EEG信号质量、视觉质量、个体是否位于训练分布内以及各模态之间的一致性。当 Q(t) 低于阈值时，即使 R(t) 较高或较低，也应显示“需要人工复核”，避免把异常设备状态解释为人员状态。", styles["body"]),
        P("系统还应区分普通风险预警和快速事件触发。长时间风险使用平滑和持续时间，严重连续闭眼、关键报警漏检等事件则允许绕过慢速平滑进入即时复核。两条路径最终均由安全规则层控制，模型不得直接执行不可逆操作。", styles["body"]),
        P("6 系统实现与数据接口", styles["h1"]),
        P("建议把采集、特征、融合和决策分为独立服务，使不同设备能够按能力接入。每个证据包至少包含数值、时间戳、有效标志、质量分数、基线版本和算法版本。前端只展示服务实际返回的状态，不通过是否显示组件来推断模态是否可用。", styles["body"]),
        academic_table([
            ["接口字段", "示例", "用途"],
            ["camera_available", "true / false", "操作员摄像头是否存在且已授权开启"],
            ["vision_quality", "0.86", "综合人脸可见、眼部置信度、照度与遮挡"],
            ["perclos_enabled", "true / false", "PERCLOS 是否满足参与评估的条件"],
            ["perclos_value", "0.24 或 null", "单位时间闭眼比例；未启用时必须为 null 而不是 0"],
            ["eeg_quality", "0.93", "电极接触、伪迹和有效通道质量"],
            ["active_modalities", "EEG, PERCLOS, TASK", "本次风险计算真实使用的证据来源"],
            ["risk_score / confidence", "69 / 0.82", "融合风险与可信度必须同时输出"],
            ["decision_state", "warning / abstain", "风险等级或拒判状态"],
        ], [40*mm, 42*mm, 92*mm], styles, font_size=7.1),
        PageBreak(),
    ]

    story += [
        P("7 模型训练与标定策略", styles["h1"]),
        P("训练建议分为三个阶段。第一阶段保留当前 RA + Tangent-LR 作为 EEG 可解释基线，但将目标被试校准改为严格因果协议，只允许使用接入时已采集的短时无标签基线或此前历史窗口。第二阶段在港口模拟任务中采集同步 EEG、操作员面部视频、异常事件响应、主观困倦量表和作业情境，形成六因子时间轴。第三阶段使用约束模型学习融合权重和风险阈值，并将基础权重作为正则化先验。", styles["body"]),
        P("权重学习不宜只优化窗口级准确率。可采用带非负约束和归一化约束的逻辑回归、序数回归或生存/事件风险模型，使权重方向可解释。若数据规模有限，应优先使用简单模型和嵌套交叉验证，避免复杂深度融合在小样本上产生虚高结果。个体化可通过群体先验加短时校准实现，而不是为每名新操作员从头训练。", styles["body"]),
        P("建议的标签体系包括三类：生理与主观标签，如清醒/困倦、KSS和睡眠信息；行为标签，如反应时间、漏检和误报；安全结果标签，如关键异常未响应、人工复核结论和交班事件。训练时可将疲劳作为潜在状态，将多源标签作为不完全观测，减少把 PERCLOS 或单一量表直接当作绝对真值的偏差。", styles["body"]),
        P("8 验证方案", styles["h1"]),
        P("验证必须回答四个问题：模型是否能跨人工作，是否能跨天保持稳定，模态缺失时是否安全退化，以及预警是否真正关联异常感知下降。建议采用以下证据梯度。", styles["body"]),
        academic_table([
            ["验证层级", "设计", "关键指标"],
            ["离线跨被试", "严格 LOSO；目标被试仅使用前置短时基线", "平衡准确率、AUROC、F1、Brier、ECE"],
            ["跨日与跨设备", "不同班次、帽式/头带式EEG、不同摄像头与照明", "性能下降、校准漂移、拒判率"],
            ["缺失模态压力测试", "断开摄像头、遮挡眼睛、降低EEG通道质量", "风险跳变量、错误自信率、恢复时间"],
            ["异常感知验证", "标准化港口异常注入并记录反应", "漏检率、反应时间、风险提前量"],
            ["在线前瞻性验证", "按时间顺序运行，不访问未来窗口", "误报/小时、严重事件漏报、报警延迟"],
            ["消融实验", "逐项移除 V、PERCLOS、质量门控、任务风险和拒判", "各模块的独立贡献与失败模式"],
        ], [32*mm, 82*mm, 60*mm], styles, font_size=7.1),
        P("基线比较至少包括 EEG-only RA + Tangent-LR、PERCLOS-only、固定权重晚期融合、无质量门控的特征拼接、代表性的跨被试领域泛化模型，以及本报告提出的质量感知动态融合。所有模型必须使用相同受试者划分和时间因果约束。", styles["body"]),
        PageBreak(),
    ]

    story += [
        P("9 预期创新、风险与研究边界", styles["h1"]),
        P("本项目可主张的创新不是“使用了黎曼流形”或“加入了PERCLOS”，而是把这些成熟证据组织为一个面向港口设备异构和安全决策的可追溯系统。更具防御性的创新表述包括：", styles["body"]),
        P("• <b>动态黎曼证据：</b>以偏离程度和偏离速度共同描述脑状态轨迹，将静态分类转化为风险演化证据。", styles["bullet"]),
        P("• <b>可选视觉模态：</b>通过可用性和质量门控决定 PERCLOS 是否进入计算，并显式重归一化权重。", styles["bullet"]),
        P("• <b>疲劳—异常感知—任务危险联合评估：</b>把人员状态与实际作业后果联系起来，而非仅预测一般困倦标签。", styles["bullet"]),
        P("• <b>安全拒判：</b>同时输出风险与置信度，在传感器失效或分布外状态下主动请求人工复核。", styles["bullet"]),
        P("• <b>港口跨日验证协议：</b>以误报/小时、漏报、预警提前量和校准成本评价真实可用性。", styles["bullet"]),
        P("主要风险包括：实验室驾驶数据与港口任务之间存在领域差异；PERCLOS 对眼镜、遮挡、侧脸和照明敏感；EEG 容易受到眼动、肌电与电极接触影响；异常事件数量稀少导致标签不平衡；任务危险等级可能依赖业务规则而非纯数据学习；个体监测涉及隐私、劳动关系和自动化决策伦理。因而，数据最小化、用途限定、访问审计、人工复核权以及模型失效告知必须进入系统设计。", styles["body"]),
        P("10 结论与近期执行清单", styles["h1"]),
        P("本报告提出六因子综合疲劳风险框架，以动态黎曼 EEG 证据为稳定底座，以 PERCLOS 和连续闭眼时长作为条件性视觉证据，并加入异常感知下降和任务危险等级。通过可用性与质量加权，系统能够适配有摄像头和无摄像头设备；通过重归一化与拒判，它避免把缺失模态误解释为低风险。该方案的价值在于把通用疲劳识别转化为可解释、可降级、可复核的港口认知安全决策流程。", styles["body"]),
        academic_table([
            ["优先级", "近期任务", "可交付结果"],
            ["P0", "把前端模态状态与后端接口字段统一", "摄像头/PERCLOS真实状态，不再依赖前端手动模拟"],
            ["P0", "将当前EEG校准改为仅使用前置基线窗口", "无未来信息的在线推理与严格LOSO结果"],
            ["P1", "实现操作员摄像头质量评估与PERCLOS原型", "60秒滑窗、连续闭眼事件、失效检测"],
            ["P1", "设计港口异常感知实验", "异常类型、出现时刻、反应时间、漏检和任务危险度标签"],
            ["P2", "完成质量感知融合和拒判", "六因子风险、动态权重、置信度和审计日志"],
            ["P2", "开展跨人、跨日、缺失模态验证", "与单模态和固定融合基线的完整比较"],
        ], [22*mm, 79*mm, 73*mm], styles, font_size=7.2),
        PageBreak(),
    ]

    story += [
        P("术语与符号表", styles["h1"]),
        academic_table([
            ["规范术语", "定义"],
            ["Riemannian Alignment, RA", "以受试者基线协方差中心对白化后的协方差进行对齐"],
            ["Tangent-LR", "黎曼切空间特征与逻辑回归分类器"],
            ["PERCLOS", "固定时间窗内眼睑达到高度闭合状态的时间比例"],
            ["模态可用性 a<sub>i</sub>", "证据源在当前时刻是否能够参与计算的二元标志"],
            ["数据质量 q<sub>i</sub>", "证据源当前可靠程度，范围为0至1"],
            ["动态权重重归一化", "移除不可用证据后，对剩余有效证据权重重新归一"],
            ["安全拒判", "证据不足或分布外时不输出确定性风险等级"],
            ["异常感知能力", "操作员发现并响应港口异常目标的行为能力"],
        ], [58*mm, 116*mm], styles, font_size=7.4),
        Spacer(1, 5 * mm),
        P("参考文献", styles["h1"]),
        P("1. Zheng, W.-L. & Lu, B.-L. A multimodal approach to estimating vigilance using EEG and forehead EOG. <i>Journal of Neural Engineering</i> 14, 026017 (2017). DOI: 10.1088/1741-2552/aa5a98.", styles["ref"]),
        P("2. United States Federal Motor Carrier Safety Administration. <i>PERCLOS: A Valid Psychophysiological Measure of Alertness As Assessed by Psychomotor Vigilance</i>. Report FHWA-MCRT-98-006 (1998). DOI: 10.21949/1502740.", styles["ref"]),
        P("3. Abe, T. et al. PERCLOS-based technologies for detecting drowsiness: current evidence and future directions. <i>Sleep Advances</i> 4, zpad006 (2023). DOI: 10.1093/sleepadvances/zpad006.", styles["ref"]),
        P("4. Liu, Z. et al. A memristor-based adaptive neuromorphic decoder for brain–computer interfaces. <i>Nature Electronics</i> 8, 180–191 (2025). DOI: 10.1038/s41928-025-01340-2.", styles["ref"]),
        P("5. Pan, J. et al. Residual Attention Capsule Network for Multimodal EEG- and EOG-Based Driver Vigilance Estimation. <i>IEEE Transactions on Instrumentation and Measurement</i> 72, 1–12 (2023). DOI: 10.1109/TIM.2023.3307756.", styles["ref"]),
        P("6. Zhi, H. et al. Supervised Contrastive Learning-Based Domain Generalization Network for Cross-Subject Motor Decoding. <i>IEEE Transactions on Biomedical Engineering</i> 72, 401–412 (2025). DOI: 10.1109/TBME.2024.3432934.", styles["ref"]),
        P("7. Huang, H. et al. Real-Time Attention Regulation and Cognitive Monitoring Using a Wearable EEG-Based BCI. <i>IEEE Transactions on Biomedical Engineering</i> 72, 716–724 (2025). DOI: 10.1109/TBME.2024.3468351.", styles["ref"]),
        P("8. Wang, W. et al. EEG-Based Cross-Subject Emotion Recognition Using Sparse Bayesian Learning With Enhanced Covariance Alignment. <i>IEEE Transactions on Affective Computing</i> 16, 1190–1204 (2025). DOI: 10.1109/TAFFC.2024.3497897.", styles["ref"]),
        P("9. Port-fatigue-dashboard model metadata. SEED-VIG-RA-TLR-v1.0.0; subject-wise Riemannian alignment, identity tangent-space features and logistic regression (research prototype, 2026).", styles["ref"]),
        Spacer(1, 8 * mm),
        callout("<b>报告状态：</b>方法设计稿，可用于课题讨论、原型开发和实验方案评审。任何生产部署前均需完成伦理审批、岗位风险评估、数据保护设计和前瞻性现场验证。", styles, RED_LIGHT),
    ]

    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build_report()
