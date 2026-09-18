from app import app


def test_login_page_is_available():
    client = app.server.test_client()
    response = client.get('/login')
    assert response.status_code == 200


def test_dashboard_requires_login():
    client = app.server.test_client()
    response = client.get('/sales-dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')
