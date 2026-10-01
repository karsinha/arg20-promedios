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


def test_standings_rows_encuentra_filas_anidadas():
    plana = {"standings": [{"team_id": 1, "played": 3, "pts": 5}]}
    por_zona = {"zones": [{"key": "playoff"}],
                "standings": {"A": [{"team_id": 2, "played": 1, "pts": 1}],
                              "B": [{"team_id": 3, "played": 2, "pts": 4}]}}
    assert [r["team_id"] for r in sync_bsd.standings_rows(plana)] == [1]
    assert sorted(r["team_id"] for r in sync_bsd.standings_rows(por_zona)) == [2, 3]
    assert sync_bsd.standings_rows(None) == []


def test_estado_en_vivo_y_suspendido():
    assert sync_bsd.estado(ev(status="inprogress")) == "en_juego"
    assert sync_bsd.estado(ev(status="abandoned")) == "suspendido"

def test_cambios_de_tolera_respuestas_vacias():
    cambios = pytest.importorskip("sync.cambios")
    assert cambios.cambios_de(None) == []
    assert cambios.cambios_de({"count": 0, "changes": []}) == []
    assert len(cambios.cambios_de({"changes": [{"change": "status", "event_id": 1}]})) == 1


def test_penales():
    assert sync_bsd.penales({"penalty_shootout": {"home": 4, "away": 3}}) == (4, 3)
    assert sync_bsd.penales({"penalty_shootout": None}) == (None, None)
    assert sync_bsd.penales(None) == (None, None)