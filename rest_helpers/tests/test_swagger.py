from rest_helpers import swagger

def test_update_none():
    d1 = {"a": 1, "b":2}
    swagger._update(d1, None)

    assert d1 == {"a": 1, "b":2}

def test_update_simple():
    d1 = {"a": 1, "b":2}
    d2 = {"c": 3, "b":5}

    swagger._update(d1, d2)

    assert d1 == {"a": 1, "b":5, "c":3}

def test_update_nested():
    d1 = {"a": 1, "b":{"A":"I","B":"II"}}
    d2 = {"c": 3, "b":{"A":"I","B":"V"}}

    swagger._update(d1, d2)

    assert d1 == {"a": 1, "b":{"A":"I","B":"V"}, "c":3}

def test_update_by_index():
    d1 = {"a": 1, "b":[1,2,3,4,5]}
    d2 = {"c": 3, "b":{1:"A"}}

    swagger._update(d1, d2)

    assert d1 == {"a": 1, "b":[1,"A",3,4,5], "c":3}

def test_update_list():
    d1 = {"a": 1, "b":[1,2,3]}
    d2 = {"c": 3, "b":[3,4,5]}

    swagger._update(d1,d2)

    assert d1 == {"a": 1, "b":[3,4,5], "c":3}

def test_update_list_append():
    d1 = {"a": 1, "b":[1,2,3]}
    d2 = {"c": 3, "b>+":[5]}

    swagger._update(d1,d2)

    assert d1 == {"a": 1, "b":[1,2,3,5], "c":3}

def test_update_list_delete_by_elem():
    d1 = {"a": 1, "b":[1,2,3]}
    d2 = {"c": 3, "b>-":[3]}

    swagger._update(d1,d2)

    assert d1 == {"a": 1, "b":[1,2], "c":3}

def test_update_list_delete_by_index():
    d1 = {"a": 1, "b":[1,2,3]}
    d2 = {"c": 3, "b>-":["[1]"]}

    swagger._update(d1,d2)

    assert d1 == {"a": 1, "b":[1,3], "c":3}