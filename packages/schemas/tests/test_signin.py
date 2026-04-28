from cstack_schemas import SignIn, SignInLocation


def test_signin_minimum_payload() -> None:
    payload: dict[str, object] = {
        "id": "signin-1",
        "createdDateTime": "2026-04-29T08:30:00Z",
        "userId": "user-1",
        "userPrincipalName": "pat@example.com",
    }
    s = SignIn.model_validate(payload)
    assert s.id == "signin-1"
    assert s.user_principal_name == "pat@example.com"


def test_signin_full_shape() -> None:
    payload: dict[str, object] = {
        "id": "signin-2",
        "createdDateTime": "2026-04-29T08:30:00Z",
        "userId": "user-1",
        "userPrincipalName": "pat@example.com",
        "appId": "app-1",
        "appDisplayName": "Microsoft Graph PowerShell",
        "clientAppUsed": "Browser",
        "ipAddress": "203.0.113.10",
        "isInteractive": True,
        "authenticationRequirement": "multiFactorAuthentication",
        "authenticationMethodsUsed": ["password", "mobileAppNotification"],
        "deviceDetail": {
            "deviceId": "dev-1",
            "operatingSystem": "Windows10",
            "browser": "Edge 120",
            "isCompliant": True,
            "isManaged": True,
            "trustType": "AzureAdJoined",
        },
        "location": {
            "city": "Auckland",
            "state": "Auckland",
            "countryOrRegion": "NZ",
            "geoCoordinates": {"latitude": -36.85, "longitude": 174.76},
        },
        "status": {"errorCode": 0, "failureReason": "Other"},
        "riskLevelDuringSignIn": "low",
        "riskState": "none",
    }
    s = SignIn.model_validate(payload)
    assert isinstance(s.location, SignInLocation)
    assert s.location.country_or_region == "NZ"
    assert s.device_detail is not None
    assert s.device_detail.is_compliant is True
    assert s.authentication_methods_used == ["password", "mobileAppNotification"]
