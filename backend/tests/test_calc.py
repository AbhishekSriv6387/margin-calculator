from app.calc import margin, parse_exp, bracket, rollup, rate_for_target
def test_verified_examples():
    assert round(margin(2694, 1800)[1], 2) == 33.18
    assert round(margin(2500, 1800)[1], 2) == 28.00
    assert round(margin(2694, 1900)[1], 2) == 29.47
def test_edges():
    assert margin(0, 100)[1] is None
    assert margin(100, 150)[0] == -50
def test_experience():
    assert round(parse_exp("7 years 7 months"), 2) == 7.58 and parse_exp("8.4 years") == 8.4 and parse_exp("5 Years") == 5
    assert bracket(6) == "6-9" and bracket(5.9) == "3-6" and bracket(20) == "12-15"
def test_rollup_is_weighted():
    assert rollup([{"rate": 100, "genus": 50}, {"rate": 300, "genus": 270}])["margin_pct"] == 20.0
def test_target_rate():
    assert round(rate_for_target(1800, 30), 2) == 2571.43

def test_person_days_respects_start_end_and_holidays():
    import datetime as d
    from app.calc import person_days
    assert person_days(2026, 10) == 22
    assert person_days(2026, 10, [d.date(2026, 10, 2)]) == 21
    assert person_days(2026, 10, [], d.date(2026, 10, 15)) == 12              # joins mid-month
    assert person_days(2026, 10, [], None, d.date(2026, 10, 9)) == 7          # leaves mid-month
    assert person_days(2026, 10, [], d.date(2026, 11, 1)) == 0                # not started yet
    assert person_days(2026, 10, [], d.date(2026, 10, 5), d.date(2026, 10, 5)) == 1
