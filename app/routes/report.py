import unicodedata
from datetime import datetime

from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import extract

from app import db
from app.models import (
    PurchaseAdjustment,
    PurchaseItem,
    PurchaseOrder,
    PurchaseOrderCategoryOverride,
    NFEntry,
    ReportCategory,
    User,
)
from app.routes.routes import bp
from app.utils import apply_adjustments


def _normalize_text(text):
    """Remove accents and lowercase for comparison."""
    if not text:
        return ""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()


def _get_last_obs_line(observacao):
    """Extract the last non-empty line from observacao."""
    if not observacao:
        return ""
    lines = [l.strip() for l in observacao.split("\n") if l.strip()]
    return lines[-1] if lines else ""


def _match_category(last_line, categories):
    """
    Match a last observation line against category names.
    Returns the category name if matched, else None.
    Uses case/accent-insensitive substring matching.
    """
    normalized_line = _normalize_text(last_line)
    if not normalized_line:
        return None

    for cat in categories:
        normalized_cat = _normalize_text(cat)
        if normalized_cat and normalized_cat in normalized_line:
            return cat
    return None


@bp.route("/purchaser-users", methods=["GET"])
@login_required
def get_purchaser_users():
    """Get list of users eligible for the purchase report.
    Admin sees all users with system_name set and role purchaser or admin.
    Non-admin sees only themselves.
    """
    try:
        if current_user.role == "admin":
            users = (
                User.query.filter(
                    User.role.in_(["purchaser", "admin"]),
                    User.system_name.isnot(None),
                    User.system_name != "",
                )
                .order_by(User.system_name)
                .all()
            )
        else:
            users = [current_user] if current_user.system_name else []

        result = []
        for u in users:
            result.append(
                {
                    "id": u.id,
                    "username": u.username,
                    "system_name": u.system_name,
                    "report_categories": [rc.name for rc in u.report_categories],
                }
            )

        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/purchase-category-report", methods=["GET"])
@login_required
def get_purchase_category_report():
    """
    Generate a purchase report grouped by category and month for a user/year.
    Also returns orders that could not be matched.
    """
    try:
        user_id = request.args.get("user_id", type=int)
        year = request.args.get("year", type=int)

        if not user_id or not year:
            return jsonify({"error": "user_id and year are required"}), 400

        # Auth check: non-admin can only view their own report
        if current_user.role != "admin" and current_user.id != user_id:
            return jsonify({"error": "Forbidden"}), 403

        # Load target user
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({"error": "User not found"}), 404

        if not target_user.system_name:
            return jsonify({"error": "User has no system_name configured"}), 400

        # Get user's report categories
        category_map = {rc.id: rc.name for rc in target_user.report_categories}
        category_names = list(category_map.values())
        if not category_names:
            return jsonify({"error": "User has no report categories configured"}), 400

        companies_param = request.args.get("companies")
        companies = []
        if companies_param:
            companies = companies_param.split(',')
            
        include_cancelled = request.args.get("include_cancelled", "false").lower() == "true"

        # Query purchase orders for this user in the given year
        query = PurchaseOrder.query.filter(
            PurchaseOrder.func_nome.ilike(f"%{target_user.system_name}%"),
            extract("year", PurchaseOrder.dt_emis) == year,
        )
        
        if companies:
            query = query.filter(PurchaseOrder.cod_emp1.in_(companies))

        orders = query.all()

        # Build the category x month matrix
        data = {cat: [0.0] * 12 for cat in category_names}
        unmatched_orders = []
        categorized_orders = []
        all_orders = []
        i = 0
        for order in orders:
            vlr_c_ipi = order.total_pedido_com_ipi or 0.0
            # Calculate total summing non-cancelled items
            items = PurchaseItem.query.filter_by(purchase_order_id=order.id).all()
            effective_total = 0.0
            for item in items:
                qty = float(item.quantidade or 0)
                canc = float(item.qtde_canc or 0)
                # TODO calcular um item cancelado parcialmente
                if include_cancelled or qty > canc:
                    effective_total += float(item.total or 0)

            if effective_total <= 0 and not include_cancelled:
                continue
            if round(effective_total, 2) != round(vlr_c_ipi, 2):
                i+=1
                print(f"{order.cod_pedc}; valor pedidos itens: {round(effective_total, 2)}; valor total: {round(vlr_c_ipi, 2)}")
            # TODO verificar se o valor do frete estão relativos ao valor do item cancelado de maneira correta
            adjustments_query = PurchaseAdjustment.query.filter_by(
                purchase_order_id=order.id
            ).all()
            if order.cod_pedc == '39208':
                print(f"Valor do frete para o pedido 39208: {order.vlr_frete_tra}")
            adjusted_total = apply_adjustments(round(vlr_c_ipi, 2), adjustments_query) + (
                order.vlr_frete_tra or 0
            )
              
                
           
            #TODO consertar o calculo de effective total pora usar seu valor
            # Use adjusted_total for the report
            report_total = adjusted_total

            # 1. Check for manual override
            override = PurchaseOrderCategoryOverride.query.filter_by(
                purchase_order_id=order.id
            ).first()
            matched_cat = None
            override_category_id = None
            if override and override.category_id in category_map:
                matched_cat = category_map[override.category_id]
                override_category_id = override.category_id
            else:
                # 2. Auto-match via observacao
                last_line = _get_last_obs_line(order.observacao)
                matched_cat = _match_category(last_line, category_names)

            # Get NF entries details
            nf_entries = NFEntry.query.filter_by(
                cod_pedc=order.cod_pedc,
                cod_emp1=order.cod_emp1
            ).all()
            nf_numbers = sorted(list(set(nfe.num_nf for nfe in nf_entries if nfe.num_nf)))
            nf_str = ", ".join(nf_numbers) if nf_numbers else ""
            nf_dates = [nfe.dt_ent for nfe in nf_entries if nfe.dt_ent]
            dt_fat_str = nf_dates[0].strftime("%d/%m/%Y") if nf_dates else ""
            
            order_data = {
                "id": order.id,
                "cod_pedc": order.cod_pedc,
                "cod_emp1": order.cod_emp1 or "",
                "dt_emis": order.dt_emis.strftime("%Y-%m-%d"),
                "dt_emis_br": order.dt_emis.strftime("%d/%m/%Y"),
                "fornecedor_descricao": order.fornecedor_descricao,
                "observacao_last_line": _get_last_obs_line(order.observacao),
                "total": round(report_total, 2),
                "override_category_id": override_category_id,
                "matched_cat": matched_cat or "SEM CATEGORIA",
                "nf": nf_str,
                "dt_fat": dt_fat_str,
                "month_idx": order.dt_emis.month - 1,
            }

            all_orders.append(order_data)

            if matched_cat is None:
                # Add to unmatched list (no category assigned)
                unmatched_orders.append(order_data)
            else:
                # Add to categorized list (has override) OR count in report
                if override:
                    # User has manually set a category - show in categorized section
                    categorized_orders.append(order_data)
                # Add to monthly data either way
                month_idx = order.dt_emis.month - 1
                data[matched_cat][month_idx] += report_total

        # Sort unmatched orders by date (most recent first) then by cod_pedc
        unmatched_orders.sort(key=lambda x: (x["dt_emis"], x["cod_pedc"]), reverse=True)
        # Sort categorized orders by date (most recent first) then by cod_pedc
        categorized_orders.sort(
            key=lambda x: (x["dt_emis"], x["cod_pedc"]), reverse=True
        )
        # Combine: uncategorized first, then categorized at the end
        all_unmatched_for_display = unmatched_orders + categorized_orders

        # Calculate totals and averages
        category_totals = {}
        category_averages = {}
        month_totals = [0.0] * 12

        for cat in category_names:
            cat_total = sum(data[cat])
            category_totals[cat] = round(cat_total, 2)
            months_with_data = sum(1 for v in data[cat] if v > 0)
            category_averages[cat] = (
                round(cat_total / months_with_data, 2) if months_with_data > 0 else 0.0
            )
            for i in range(12):
                month_totals[i] += data[cat][i]

        for cat in category_names:
            data[cat] = [round(v, 2) for v in data[cat]]
        month_totals = [round(v, 2) for v in month_totals]

        grand_total = round(sum(month_totals), 2)
        print(f"Total de pedidos com valor diferente: {i}")
        return jsonify(
            {
                "user_name": target_user.system_name,
                "year": year,
                "categories": [{"id": k, "name": v} for k, v in category_map.items()],
                "category_names": category_names,
                "months": list(range(1, 13)),
                "data": data,
                "category_totals": category_totals,
                "category_averages": category_averages,
                "month_totals": month_totals,
                "grand_total": grand_total,
                "unmatched_orders": all_unmatched_for_display,
                "unmatched_orders_count": len(unmatched_orders),
                "all_orders": all_orders,
                "generated_at": datetime.now()
                .strftime("%d de %B de %Y")
                .replace("January", "Janeiro")
                .replace("February", "Fevereiro")
                .replace("March", "Marco")
                .replace("April", "Abril")
                .replace("May", "Maio")
                .replace("June", "Junho")
                .replace("July", "Julho")
                .replace("August", "Agosto")
                .replace("September", "Setembro")
                .replace("October", "Outubro")
                .replace("November", "Novembro")
                .replace("December", "Dezembro"),
            }
        ), 200

    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@bp.route("/purchase-category-override", methods=["POST"])
@login_required
def save_purchase_category_override():
    """Save manual category assignment for a purchase order."""
    try:
        data = request.json
        purchase_order_id = data.get("purchase_order_id")
        category_id = data.get("category_id")

        if not purchase_order_id or not category_id:
            return jsonify(
                {"error": "purchase_order_id and category_id are required"}
            ), 400

        # Check if already exists
        override = PurchaseOrderCategoryOverride.query.filter_by(
            purchase_order_id=purchase_order_id
        ).first()
        if override:
            override.category_id = category_id
            override.created_by_id = current_user.id
            override.created_at = datetime.now()
        else:
            override = PurchaseOrderCategoryOverride(
                purchase_order_id=purchase_order_id,
                category_id=category_id,
                created_by_id=current_user.id,
            )
            db.session.add(override)

        db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
