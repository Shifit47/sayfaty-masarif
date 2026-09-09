# -*- coding: utf-8 -*-
"""سيفتي — تطبيق مصاريف الشباب (موبايل)."""

import flet as ft

import storage


def money_str(v):
    return f"{storage.fmt(v)} {storage.currency()}"


# =====================================================================
# VIEW: المصاريف
# =====================================================================
class ExpensesView:
    def __init__(self, page, app):
        self.page = page
        self.app = app
        self.list = ft.ListView(expand=True, padding=6, spacing=6)
        self.day = ft.TextField(label="التاريخ", value=storage.today_str().replace("-", "/"), width=150, dense=True)
        self.amount = ft.TextField(
            label="المبلغ", value="", keyboard_type=ft.KeyboardType.NUMBER, width=160, dense=True
        )
        members = [m["name"] for m in storage.list_members()]
        self.paid_by = ft.Dropdown(width=170, dense=True)
        self.cat = ft.Dropdown(width=180, dense=True)
        self.kind = ft.SegmentedButton(
            selected={"مشترك"},
            segments=[
                ft.Segment(value="مشترك", label=ft.Text("مشترك")),
                ft.Segment(value="فردي", label=ft.Text("فردي")),
            ],
        )
        self.desc = ft.TextField(label="البيان / وصف", hint_text="إيجار الشقة مثلًا", expand=True, dense=True)
        self.refill_lists(members)

    def refill_lists(self, members=None):
        members = members if members is not None else [m["name"] for m in storage.list_members()]
        self.paid_by.options = [ft.dropdown.Option(n) for n in members]
        self.cat.options = [ft.dropdown.Option(c) for c in storage.list_categories()]

    def build(self):
        add_btn = ft.FilledButton(
            "أضف المصروف",
            icon=ft.Icons.ADD_CIRCLE_OUTLINE,
            on_click=self.on_add,
            disabled=not self.app.has_members(),
        )
        form = ft.Container(
            content=ft.Column(
                [
                    ft.Row([self.day, self.amount], spacing=8),
                    self.desc,
                    ft.Row([self.paid_by, self.cat], spacing=8),
                    ft.Row([self.kind, add_btn], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Divider(height=10),
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=10,
            bgcolor=ft.Colors.TEAL_50,
            border_radius=10,
        )
        return ft.Column([form, ft.Text("آخر المصاريف", weight=ft.FontWeight.BOLD), ft.expand(self.list)])

    def refresh(self):
        self.reload_list()

    def reload_list(self):
        self.list.controls.clear()
        rows = storage.list_expenses(limit=100)
        for e in rows:
            color = ft.Colors.BLUE_50 if e["kind"] == "مشترك" else ft.Colors.ORANGE_50
            self.list.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.RECEIPT_LONG, color=ft.Colors.TEAL_700),
                            ft.expand(
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Text(e["description"], weight=ft.FontWeight.BOLD, expand=True),
                                                ft.Text(money_str(e["amount"]), weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_900),
                                            ]
                                        ),
                                        ft.Row(
                                            [
                                                ft.Text(f'{e["day"].replace("-", "/")} • {e["paid_by"]} • {e["kind"]}'),
                                                ft.Text(e["category"], size=11, color=ft.Colors.GREY_700),
                                            ],
                                            spacing=4,
                                        ),
                                    ],
                                    spacing=2,
                                ),
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE,
                                icon_color=ft.Colors.RED_400,
                                on_click=lambda ev, id=e["id"]: self.delete(id),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                    ),
                    padding=10,
                    bgcolor=color,
                    border_radius=8,
                )
            )
        if not rows:
            self.list.controls.append(ft.Text("مفيش مصاريف لسه — أضف أول واحد فوق 👆", color=ft.Colors.GREY, italic=True))
        self.page.update()

    def on_add(self, e):
        try:
            amount = float(self.amount.value.replace(",", ""))
        except ValueError:
            self.app.snack("اكتب المبلغ كويس 😅")
            return
        if amount <= 0 or not self.amount.value.strip():
            self.app.snack("المبلغ لازم يكون أكبر من صفر")
            return
        day = self.day.value.strip().replace("/", "-")
        if len(day) == 10 and day[2:3] == "-" and day[5:6] == "-":
            pass
        else:
            day = storage.today_str()
        paid = self.paid_by.value
        if not paid:
            self.app.snack("اختار مين دفع")
            return
        kind = next(iter(self.kind.selected), "مشترك")
        storage.add_expense(
            day,
            self.desc.value or "بدون وصف",
            self.cat.value or storage.list_categories()[0],
            amount,
            paid,
            kind,
        )
        self.amount.value = ""
        self.desc.value = ""
        self.app.snack(f"اتضاف {money_str(amount)} ✅")
        self.app.refresh_all()

    def delete(self, eid):
        storage.delete_expense(eid)
        self.app.snack("اتمسح ✅")
        self.app.refresh_all()


# =====================================================================
# VIEW: الأعضاء
# =====================================================================
class MembersView:
    def __init__(self, page, app):
        self.page = page
        self.app = app
        self.list = ft.ListView(expand=True, padding=6, spacing=6)

    def build(self):
        add_btn = ft.FilledButton("زود عضو", icon=ft.Icons.PERSON_ADD_ALT_1, on_click=self.add_dialog)
        cur = ft.TextField(
            label="العملة",
            value=storage.currency(),
            width=110,
            dense=True,
            on_blur=self.save_currency,
        )
        head = ft.Row([add_btn, cur], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        return ft.Column([head, ft.expand(self.list)])

    def save_currency(self, e):
        storage.set_currency(e.control.value.strip())
        self.app.refresh_all()

    def refresh(self):
        self.reload_list()

    def reload_list(self):
        members = storage.list_members()
        self.list.controls.clear()
        for m in members:
            self.list.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.CircleAvatar(
                                content=ft.Text(m["name"][0] if m["name"] else "؟", color=ft.Colors.WHITE),
                                bgcolor=ft.Colors.TEAL_700,
                            ),
                            ft.expand(
                                ft.Column(
                                    [
                                        ft.Text(m["name"], weight=ft.FontWeight.BOLD, size=16),
                                        ft.Text(f'العهدة: {money_str(m["advance"])}', size=12, color=ft.Colors.GREY_700),
                                    ],
                                    spacing=2,
                                )
                            ),
                            ft.IconButton(ft.Icons.EDIT_OUTLINED, on_click=lambda ev, id=m["id"]: self.edit_dialog(id)),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE,
                                icon_color=ft.Colors.RED_400,
                                on_click=lambda ev, id=m["id"]: self.delete_dialog(id),
                            ),
                        ]
                    ),
                    padding=10,
                    bgcolor=ft.Colors.GREEN_50,
                    border_radius=8,
                )
            )
        if not members:
            self.list.controls.append(
                ft.Text("مفيش أعضاء — زود عضو الأول 🙂", color=ft.Colors.GREY, italic=True)
            )
        self.page.update()

    def add_dialog(self, e):
        self._dialog(None)

    def edit_dialog(self, mid):
        m = next((x for x in storage.list_members() if x["id"] == mid), None)
        if m:
            self._dialog(m)

    def delete_dialog(self, mid):
        m = next((x for x in storage.list_members() if x["id"] == mid), None)
        if not m:
            return
        dlg = ft.AlertDialog(
            title=ft.Text("احذف العضو؟"),
            content=ft.Text(f"هتتحدف {m['name']}.. القوائم هتتجدد. تمام؟"),
            modal=True,
            actions=[
                ft.TextButton("إلغاء", on_click=lambda ev: self.page.close(dlg)),
                ft.FilledButton(
                    "احذف",
                    on_click=lambda ev: (self.page.close(dlg), storage.delete_member(mid), self.app.refresh_all()),
                ),
            ],
        )
        self.page.open(dlg)

    def _dialog(self, member):
        name = ft.TextField(label="الاسم", value=member["name"] if member else "", autofocus=True)
        adv = ft.TextField(
            label=f'العهدة ({storage.currency()})',
            value=str(member["advance"]) if member else "0",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        note = ft.TextField(label="ملاحظة (اختياري)", value=member["note"] if member else "", dense=True)
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("تعديل العضو" if member else "عضو جديد"),
            content=ft.Column([name, adv, note], tight=True, width=260),
            actions=[
                ft.TextButton("إلغاء", on_click=lambda ev: self.page.close(dlg)),
                ft.FilledButton(
                    "حفظ",
                    on_click=lambda ev: self._save(dlg, name.value, adv.value, note.value, member["id"] if member else None),
                ),
            ],
        )
        self.page.open(dlg)

    def _save(self, dlg, name, adv, note, mid):
        name = name.strip()
        try:
            advance = float(adv.replace(",", ""))
        except ValueError:
            advance = 0.0
        if not name:
            self.app.snack("اكتب اسم العضو")
            return
        try:
            if mid is None:
                storage.add_member(name, advance, note)
            else:
                storage.update_member(mid, name, advance, note)
        except Exception:
            self.app.snack("الاسم دا موجود خلاص")
            return
        self.page.close(dlg)
        self.app.refresh_all()


# =====================================================================
# VIEW: التسويات
# =====================================================================
class SettlementsView:
    def __init__(self, page, app):
        self.page = page
        self.app = app
        self.list = ft.ListView(expand=True, padding=6, spacing=6)
        self.day = ft.TextField(label="التاريخ", value=storage.today_str().replace("-", "/"), width=150, dense=True)
        self.amount = ft.TextField(label="المبلغ", keyboard_type=ft.KeyboardType.NUMBER, width=160, dense=True)
        self.payer = ft.Dropdown(width=170, dense=True)
        self.receiver = ft.Dropdown(width=170, dense=True)
        self.note = ft.TextField(label="ملاحظة (اختياري)", dense=True, expand=True)
        self.refill()

    def refill(self):
        names = [m["name"] for m in storage.list_members()]
        self.payer.options = [ft.dropdown.Option(n) for n in names]
        self.receiver.options = [ft.dropdown.Option(n) for n in names]

    def build(self):
        add_btn = ft.FilledButton("سجّل التسوية", icon=ft.Icons.SWAP_HORIZ, on_click=self.on_add)
        form = ft.Container(
            content=ft.Column(
                [
                    ft.Row([self.day, self.amount], spacing=8),
                    ft.Row(
                        [ft.Text("من", width=40), ft.expand(self.payer), ft.Text("إلى", width=40), ft.expand(self.receiver)],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self.note,
                    ft.Row([add_btn], alignment=ft.MainAxisAlignment.CENTER),
                ],
                spacing=8,
            ),
            padding=10,
            bgcolor=ft.Colors.PURPLE_50,
            border_radius=10,
        )
        return ft.Column([form, ft.Text("سجل التسويات", weight=ft.FontWeight.BOLD), ft.expand(self.list)])

    def refresh(self):
        self.refill()
        self.reload_list()

    def reload_list(self):
        self.list.controls.clear()
        for s in storage.list_settlements(limit=100):
            self.list.controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(ft.Icons.SWAP_HORIZ, color=ft.Colors.PURPLE_700),
                            ft.expand(
                                ft.Column(
                                    [
                                        ft.Text(
                                            f'{s["payer"]} ← {s["receiver"]}',
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            f'{s["day"].replace("-", "/")} • {money_str(s["amount"])}'
                                            + (f' • {s["note"]}' if s["note"] else ""),
                                            size=12,
                                            color=ft.Colors.GREY_700,
                                        ),
                                    ],
                                    spacing=2,
                                )
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE,
                                icon_color=ft.Colors.RED_400,
                                on_click=lambda ev, id=s["id"]: self.delete(id),
                            ),
                        ]
                    ),
                    padding=10,
                    bgcolor=ft.Colors.PURPLE_50,
                    border_radius=8,
                )
            )
        if not storage.list_settlements(limit=1):
            self.list.controls.append(
                ft.Text("مفيش تسويات لسه — سجّل أي تحويل نقدي هنا 💸", color=ft.Colors.GREY, italic=True)
            )
        self.page.update()

    def on_add(self, e):
        try:
            amount = float(self.amount.value.replace(",", ""))
        except ValueError:
            self.app.snack("اكتب المبلغ كويس 😅")
            return
        if amount <= 0:
            self.app.snack("المبلغ لازم يكون أكبر من صفر")
            return
        payer = self.payer.value
        receiver = self.receiver.value
        if not payer or not receiver:
            self.app.snack("اختار اللي دفع واللي استلم")
            return
        if payer == receiver:
            self.app.snack("اللي دفع = اللي استلم؟ 😅")
            return
        day = self.day.value.strip().replace("/", "-")
        if len(day) != 10 or day[2:3] != "-" or day[5:6] != "-":
            day = storage.today_str()
        storage.add_settlement(day, payer, receiver, amount, self.note.value or "")
        self.amount.value = ""
        self.note.value = ""
        self.app.snack(f"تسوية {money_str(amount)} اتسجلت ✅")
        self.app.refresh_all()

    def delete(self, sid):
        storage.delete_settlement(sid)
        self.app.snack("اتمسحت ✅")
        self.app.refresh_all()


# =====================================================================
# VIEW: الملخص
# =====================================================================
class SummaryView:
    def __init__(self, page, app):
        self.page = page
        self.app = app
        self.box = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=6)

    def build(self):
        return self.box

    def refresh(self):
        s = storage.summary()
        controls = []

        def card(title, value, color=ft.Colors.TEAL_800):
            return ft.Container(
                content=ft.Row(
                    [ft.Text(title, color=ft.Colors.GREY_800), ft.expand(), ft.Text(value, weight=ft.FontWeight.BOLD, color=color, size=16)],
                ),
                padding=10,
                bgcolor=ft.Colors.WHITE,
                border_radius=8,
            )

        controls.append(card("إجمالي المصاريف", money_str(s["total_all"])))
        controls.append(card("مشترك (على كل الأعضاء)", money_str(s["total_shared"])))
        controls.append(card("العهدة الكلية", money_str(s["total_advance"])))
        controls.append(card(f'نصيب كل عضو ({s["count"]})', money_str(s["share_each"])))

        controls.append(
            ft.Container(
                content=ft.Text("الرصيد النهائي لكل عضو", weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_900),
                padding=6,
                bgcolor=ft.Colors.TEAL_50,
                border_radius=8,
            )
        )
        for r in s["rows"]:
            net = r["net"]
            netcolor = ft.Colors.GREEN_800 if net > 0 else ft.Colors.RED_900 if net < 0 else ft.Colors.GREY_700
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.CircleAvatar(
                                        content=ft.Text(r["name"][0], color=ft.Colors.WHITE),
                                        bgcolor=ft.Colors.TEAL_700,
                                        radius=14,
                                    ),
                                    ft.Text(r["name"], weight=ft.FontWeight.BOLD, expand=True),
                                    ft.Text(money_str(net), weight=ft.FontWeight.BOLD, size=17, color=netcolor),
                                ]
                            ),
                            ft.Row(
                                [
                                    ft.Text(f'العهدة: {money_str(r["advance"])}', size=11, color=ft.Colors.GREY_700),
                                    ft.Text(f'دفع مشترك: {money_str(r["paid_shared"])}', size=11, color=ft.Colors.GREY_700),
                                ],
                                spacing=8,
                            ),
                            ft.Row(
                                [
                                    ft.Text(f'استلم: {money_str(r["received"])}', size=11, color=ft.Colors.GREY_600),
                                    ft.Text(f'دفع: {money_str(r["paid_out"])}', size=11, color=ft.Colors.GREY_600),
                                ],
                                spacing=8,
                            ),
                        ],
                        spacing=3,
                    ),
                    padding=10,
                    bgcolor=ft.Colors.GREEN_50 if net >= 0 else ft.Colors.ORANGE_50,
                    border_radius=8,
                )
            )

        # جملة التسوية لاتنين
        if s["count"] == 2:
            a, b = s["rows"][0], s["rows"][1]
            if a["net"] > 0:
                msg = f'{a["name"]} يستحق من {b["name"]} مبلغ {money_str(a["net"])}'
            elif a["net"] < 0:
                msg = f'{b["name"]} يستحق من {a["name"]} مبلغ {money_str(-a["net"])}'
            else:
                msg = "متساويان تمام 👌"
            controls.append(
                ft.Container(
                    content=ft.Text(msg, weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
                    bgcolor=ft.Colors.RED_600 if a["net"] != 0 else ft.Colors.GREEN_700,
                    padding=14,
                    border_radius=10,
                )
            )

        if s["count"] >= 3:
            controls.append(
                ft.Container(
                    content=ft.Text(
                        "اللي رصيده موجب يستلم من اللي رصيدهم سالب — سهلوا بينكم 👌",
                        size=12,
                        color=ft.Colors.GREY_700,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    bgcolor=ft.Colors.GREY_100,
                    padding=8,
                    border_radius=8,
                )
            )

        # توزيع الفئات
        controls.append(
            ft.Container(
                content=ft.Text("المصاريف حسب الفئة", weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_900),
                padding=6,
                bgcolor=ft.Colors.TEAL_50,
                border_radius=8,
            )
        )
        for cat, tot in sorted(s["categories"].items(), key=lambda x: -x[1]):
            if tot <= 0:
                continue
            controls.append(
                ft.Container(
                    content=ft.Row(
                        [ft.Text(cat, expand=True), ft.Text(money_str(tot), weight=ft.FontWeight.BOLD, color=ft.Colors.TEAL_900)]
                    ),
                    padding=8,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=8,
                )
            )

        self.box.controls = controls
        self.page.update()


# =====================================================================
# APP
# =====================================================================
class SayfatyApp:
    def __init__(self):
        self.exp = None
        self.mem = None
        self.stl = None
        self.summary = None
        self.nav = None
        self.views = {}
        self.pages = []

    def snack(self, msg):
        self.page.show_snack_bar(ft.SnackBar(ft.Text(msg), bgcolor=ft.Colors.TEAL_900))

    def has_members(self):
        return bool(storage.list_members())

    def refresh_all(self):
        for v in self.pages:
            if v is not None:
                v.refresh()
        # أعد بناء حالة الأزرار حسب عدد الأعضاء

    def on_nav(self, e):
        idx = e.control.selected_index
        self.show_view(idx)

    def show_view(self, idx):
        for i, v in enumerate(self.pages):
            if v is not None:
                v.visible = i == idx
        self.page.update()

    def main(self, page: ft.Page):
        self.page = page
        page.title = "سيفتي — الميزانية"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL)
        page.padding = 4
        page.appbar = ft.AppBar(
            title=ft.Text("💰 سيفتي", color=ft.Colors.WHITE),
            bgcolor=ft.Colors.TEAL_800,
            center_title=True,
        )

        self.exp = ExpensesView(page, self)
        self.mem = MembersView(page, self)
        self.stl = SettlementsView(page, self)
        self.summary = SummaryView(page, self)
        self.pages = [self.exp, self.mem, self.stl, self.summary]

        for v in self.pages:
            v.visible = False
            page.add(v.build())

        self.nav = ft.NavigationBar(
            selected_index=0,
            label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
            on_change=self.on_nav,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.RECEIPT_SHARP, selected_icon=ft.Icons.RECEIPT_LONG, label="المصاريف"),
                ft.NavigationBarDestination(icon=ft.Icons.PEOPLE_OUTLINE, selected_icon=ft.Icons.PEOPLE, label="الأعضاء"),
                ft.NavigationBarDestination(icon=ft.Icons.SWAP_HORIZ, selected_icon=ft.Icons.SWAP_HORIZ_ROUNDED, label="التسويات"),
                ft.NavigationBarDestination(icon=ft.Icons.PIE_CHART_OUTLINE, selected_icon=ft.Icons.PIE_CHART, label="الملخص"),
            ],
        )
        page.navigation_bar = self.nav

        # إعدادات أول تشغيل
        if not storage.get_setting("seeded"):
            if not storage.list_members():
                storage.add_member("أحمد", 0)
                storage.add_member("محمد", 0)
            storage.set_setting("seeded", "1")

        page.show_view = self.show_view
        page.find_view = lambda i: self.pages[i]
        page.go = self.show_view

        self.exp.refresh()
        self.mem.refresh()
        self.stl.refresh()
        self.summary.refresh()
        self.show_view(0)


def main():
    ft.app(target=SayfatyApp().main)


if __name__ == "__main__":
    main()