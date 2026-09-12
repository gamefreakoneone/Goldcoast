from goldcoast.data import SeedData
from goldcoast.models.pipeline import HypeMoment
from goldcoast.models.seed import AdStyle


def eligible_styles(moment: HypeMoment, seed: SeedData) -> list[AdStyle]:
    description = moment.description.casefold()
    tags = {moment.sport.casefold()}
    categories = {
        "victory": ("win", "victory", "celebrat", "ovation", "final", "conclude"),
        "precision": ("precis", "sticks", "stuck", "bullseye"),
        "comeback": ("comeback", "recover", "behind"),
        "record": ("record", "historic"),
        "crowd_roar": ("cheer", "roar", "ovation"),
        "stuck_landing": ("sticks", "stuck", "landing"),
    }
    tags.update(name for name, words in categories.items() if any(w in description for w in words))
    return [style for style in seed.ad_styles.values() if tags & set(style.use_when)]
