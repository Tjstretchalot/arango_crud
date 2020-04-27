from .clusters import WeightedRandomCluster, RandomCluster  # noqa: F401
from .back_off_strategies import StepBackOffStrategy  # noqa: F401
from .auths import BasicAuth, JWTAuth, JWTDiskCache  # noqa: F401
from .config import Config  # noqa: F401
from .env_config import env_config  # noqa: F401

import os
import logging

if os.environ.get('ARANGO_APPLY_BASIC_CONFIG') == 'true':
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
    )
