from requests import Session, Response
from vscodl import constants


def init(session: Session) -> Response:
    """Request to set necessary VSCO cookies."""
    return session.get(
        constants.VSCO_URL + "/ajx/gallery",
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


def get_articles(session: Session, uid: str, site_id: str, size: int, page: int) -> object:
    """Gets paginated articles of user."""
    return session.get(
        constants.VSCO_URL + "/ajxp/{}/2.0/articles?site_id={}&size={}&page={}".format(uid, site_id, size, page),
        headers={"Referer": constants.VSCO_URL, "User-Agent": constants.USER_AGENT}
    ).json()


def download_url(session: Session, url: str, use_host_header=True) -> Response:
    """Sends response for downloading media."""
    return session.get(url, headers={"Host": constants.VSCO_IMAGE_SITENAME} if use_host_header else {})
