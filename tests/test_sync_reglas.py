"""Reglas de sync_bsd.py (corren despues de mover el archivo a sync/ con scripts/migrar_estructura.sh)."""
import pytest

sync_bsd = pytest.importorskip("sync.sync_bsd")


def ev(**kw):
    base = {"id": 1, "stage": "group-stage", "round_number": 11, "home_team_id": 10, "away_team_id": 20,
            "status": "notstarted", "event_date": "2026-08-01T20:00:00Z"}
    return {**base, **kw}


def test_apertura_y_clausura_se_separan_por_fecha():
    assert sync_bsd.tipo_torneo(ev(event_date="2026-06-14T23:00:00Z")) == "apertura"
    assert sync_bsd.tipo_torneo(ev(event_date="2026-06-15T00:00:00Z")) == "clausura"


def test_fase_playoff_vs_zona():
    assert sync_bsd.fase(ev(stage="quarterfinals")) == "playoff"
    assert sync_bsd.fase(ev(stage="league-phase")) == "zona"


def test_postergado_con_reemplazo_se_marca_reprogramado():
    orig = ev(id=223766, status="postponed")
    nuevo = ev(id=604493, status="notstarted", event_date="2026-10-07T20:00:00Z")
    assert sync_bsd.marcar_reprogramados([orig, nuevo]) == {223766}


def test_postergado_sin_reemplazo_no_se_marca():
    assert sync_bsd.marcar_reprogramados([ev(id=5, status="postponed")]) == set()
