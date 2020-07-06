import constants
from requests import Session, Response


def user_info(session: Session) -> Response:
    """User about currently logged-in user"""
    return session.get(
        constants.VSCO_URL + "/content/Static/userinfo",
        headers={"Referer": constants.VSCO_URL, "User-Agent": constants.USER_AGENT}
    )


def get_sites(session: Session, uid: str, username: str) -> object:
    """Get a user's sites"""
    return session.get(constants.VSCO_URL + "/ajxp/{}/2.0/sites?subdomain={}".format(uid, username)).json()["sites"]


def get_medias(session: Session, uid: str, site_id: str, size: int, page: int) -> object:
    """Gets paginated medias of user."""
    return session.get(
        constants.VSCO_URL + "/ajxp/{}/2.0/medias?site_id={}&size={}&page={}".format(uid, site_id, size, page),
        headers={"Referer": constants.VSCO_URL, "User-Agent": constants.USER_AGENT}
    ).json()


def download_url(session: Session, url: str) -> Response:
    """Sends response for downloading media."""
    return session.get(url, headers={"Host": constants.VSCO_IMAGE_SITENAME})