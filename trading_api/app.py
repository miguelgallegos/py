from flask import Flask, jsonify, request

from services.portfolio_service import get_portfolio
from services.trade_service import execute_trade

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route("/trade", methods=["POST"])
def trade():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify({"error": "JSON body is required"}), 400

    try:
        response = execute_trade(payload)
        return jsonify({"success": True, "data": response}), 200
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/portfolio", methods=["GET"])
def portfolio():
    exchange_name = request.args.get("exchange")
    try:
        response = get_portfolio(exchange_name)
        return jsonify({"success": True, "data": response}), 200
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
