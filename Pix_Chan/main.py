import asyncio
import math
from typing import List, NamedTuple

import httpx


async def captcha(proxy: str = None):
    response = (
        await httpx.AsyncClient(proxy=proxy).get(
            "https://www.google.com/recaptcha/api2/anchor?ar=1&k=6Ld_hskiAAAAADfg9HredZvZx8Z_C8FrNJ519Rc6&co=aHR0cHM6Ly9waXhhaS5hcnQ6NDQz&hl=ja&v=aR-zv8WjtWx4lAw-tRCA-zca&size=invisible&cb=u2wj0bvs99s6",
        )
    ).text
    recaptcha_token = response.split('recaptcha-token" value="')[1].split('">')[0]
    payload = {
        "v": "aR-zv8WjtWx4lAw-tRCA-zca",
        "reason": "q",
        "c": recaptcha_token,
        "k": "6Ld_hskiAAAAADfg9HredZvZx8Z_C8FrNJ519Rc6",
        "co": "aHR0cHM6Ly9waXhhaS5hcnQ6NDQz",
        "hl": "en",
        "size": "invisible",
        "chr": "",
        "vh": "",
        "bg": "",
    }

    response = (
        await httpx.AsyncClient(proxy=proxy).post(
            "https://www.google.com/recaptcha/api2/reload?k=6Ld_hskiAAAAADfg9HredZvZx8Z_C8FrNJ519Rc6",
            data=payload,
        )
    ).text
    try:
        token = response.split('"rresp","')[1].split('"')[0]
    except Exception:
        return False

    return token


class PixError(Exception):
    pass


class UserInfo(NamedTuple):
    email: str
    email_verified: bool


class Model(NamedTuple):
    id: str
    latest_version_id: str
    title: str
    type: str


class ModelVersion(NamedTuple):
    negative_prompts: str
    sampling_method: str
    sampling_steps: int
    cfg_scale: int


class PixAI:
    def __init__(self, proxy: str = None):
        self.proxy = proxy
        self.session = httpx.AsyncClient(proxy=proxy, timeout=None)

    async def initialize(
        self,
        email: str,
        password: str,
        login: bool = True,
        token: str = None,
    ) -> None:
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/json",
            "Origin": "https://pixai.art",
            "Priority": "u=1, i",
            "Referer": "https://pixai.art/",
            "Sec-Ch-Ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)  AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0  Safari/537.36",
        }

        if token:
            self.token = token
            self.headers["authorization"] = f"Bearer {self.token}"
            self.user_id = None
        else:
            payload = {
                "query": "\n    mutation register($input: RegisterOrLoginInput!) {\n  register(input: $input) {\n    ...UserBase\n  }\n}\n    \n    fragment UserBase on User {\n  id\n  email\n  emailVerified\n  username\n  displayName\n  createdAt\n  updatedAt\n  avatarMedia {\n    ...MediaBase\n  }\n  membership {\n    membershipId\n    tier\n  }\n  isAdmin\n}\n    \n\n    fragment MediaBase on Media {\n  id\n  type\n  width\n  height\n  urls {\n    variant\n    url\n  }\n  imageType\n  fileUrl\n  duration\n  thumbnailUrl\n  hlsUrl\n  size\n  flag {\n    ...ModerationFlagBase\n  }\n}\n    \n\n    fragment ModerationFlagBase on ModerationFlag {\n  status\n  isSensitive\n  isMinors\n  isRealistic\n  isFlagged\n  isSexyPic\n  isSexyText\n  shouldBlur\n  isWarned\n}\n    ",
                "variables": {
                    "input": {
                        "email": email,
                        "password": password,
                        "recaptchaToken": await captcha(self.proxy),
                    }
                },
            }

            if not payload["variables"]["input"]["recaptchaToken"]:
                raise PixError("キャプチャー失敗")

            if login:
                payload["query"] = (
                    "\n    mutation login($input: RegisterOrLoginInput!) {\n  login(input: $input) {\n    ...UserDetail\n  }\n}\n    \n    fragment UserDetail on User {\n  ...UserBase\n  coverMedia {\n    ...MediaBase\n  }\n  followedByMe\n  followingMe\n  followerCount\n  followingCount\n  inspiredCount\n}\n    \n\n    fragment UserBase on User {\n  id\n  email\n  emailVerified\n  username\n  displayName\n  createdAt\n  updatedAt\n  avatarMedia {\n    ...MediaBase\n  }\n  membership {\n    membershipId\n    tier\n  }\n  isAdmin\n}\n    \n\n    fragment MediaBase on Media {\n  id\n  type\n  width\n  height\n  urls {\n    variant\n    url\n  }\n  imageType\n  fileUrl\n  duration\n  thumbnailUrl\n  hlsUrl\n  size\n  flag {\n    ...ModerationFlagBase\n  }\n}\n    \n\n    fragment ModerationFlagBase on ModerationFlag {\n  status\n  isSensitive\n  isMinors\n  isRealistic\n  isFlagged\n  isSexyPic\n  isSexyText\n  shouldBlur\n  isWarned\n}\n    "
                )

            response = await self.session.post(
                "https://api.pixai.art/graphql",
                headers=self.headers,
                json=payload,
            )
            if "errors" in response.json():
                raise PixError(response.json())

            self.token = response.headers["Token"]
            self.headers["authorization"] = f"Bearer {self.token}"

            if not login:
                self.user_id = response.json()["data"]["register"]["id"]
                age_payload = {
                    "query": "\n    mutation setPreferences($value: JSONObject!) {\n  setPreferences(value: $value)\n}\n    ",
                    "variables": {
                        "value": {
                            "experienceLevel": "beginner",
                            "ageVerificationStatus": "OVER18",
                        }
                    },
                }
                response = await self.session.post(
                    "https://api.pixai.art/graphql",
                    headers=self.headers,
                    json=age_payload,
                )
            else:
                self.user_id = response.json()["data"]["login"]["id"]

    async def send_verification_code(self):
        payload = {
            "operationName": "genCode",
            "variables": {
                "input": {
                    "intent": "VerifyEmail",
                    "approach": "Email",
                    "origin": "https://pixai.art",
                }
            },
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "ac634799140abee1174bb9d37fe220dca757adf1501c4b3aa84d77c6c7b69802",
                }
            },
        }

        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        if "errors" in response.json():
            raise PixError(response.json())

    async def verify_code(self, code: str):
        payload = {
            "operationName": "verifyEmail",
            "variables": {"code": code},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "5231965992b3bcd70a1d8ae40a1b25b3bb579e291903acb984f14f13b0eaa455",
                }
            },
        }

        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        if "errors" in response.json():
            raise PixError(response.json())

    async def get_user_info(self):
        payload = {
            "operationName": "getUserInfo",
            "variables": {},
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "87316e816ee97f155f711cabaff32584ccb7152cea7d7b8a0e6a9f1742220b25",
                }
            },
        }

        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        if "errors" in response.json():
            raise PixError(response.json())
        user_info = response.json()["data"]["me"]

        return UserInfo(user_info["email"], user_info["emailVerified"])

    async def get_quota(self):
        payload = {
            "query": "\n    query getMyQuota {\n  me {\n    quotaAmount\n  }\n}\n    ",
            "variables": {},
        }
        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        if "errors" in response.json():
            raise PixError(response.json())

        return int(response.json()["data"]["me"]["quotaAmount"])

    async def get_media(self, media_id: str):
        payload = {
            "query": "\n    query getMedia($id: String!) {\n  media(id: $id) {\n    ...MediaBase\n  }\n}\n    \n    fragment MediaBase on Media {\n  id\n  type\n  width\n  height\n  urls {\n    variant\n    url\n  }\n  imageType\n  fileUrl\n  duration\n  thumbnailUrl\n  hlsUrl\n  size\n  flag {\n    ...ModerationFlagBase\n  }\n}\n    \n\n    fragment ModerationFlagBase on ModerationFlag {\n  status\n  isSensitive\n  isMinors\n  isRealistic\n  isFlagged\n  isSexyPic\n  isSexyText\n  shouldBlur\n  isWarned\n}\n    ",
            "variables": {"id": media_id},
        }

        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        if "errors" in response.json():
            raise PixError(response.json())

        return response.json()["data"]["media"]["urls"][0]["url"]

    async def claim_daily_quota(self):
        payload = {
            "query": "\n    mutation dailyClaimQuota {\n  dailyClaimQuota\n}\n    "
        }
        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        if "errors" in response.json():
            raise PixError(response.json())

        return response.json()

    async def claim_questionnaire_quota(self, wait: int = 3):
        form_data = {
            "entry.64278853": self.user_id,
            "entry.2090837715": "趣味に身を投じる人",
            "entry.238512000": "18-25",
            "entry.1451582794": "日本",
            "entry.571931610": "AI生成ツールをほとんど使ったことがない",
            "entry.1078511207": "Twitter",
            "entry.1446121912": "好きなキャラクター",
            "entry.2087342135": "カートゥーン",
            "entry.1264482712": "壁紙・プロフィール画像用",
            "entry.1293236062": "7",
        }
        await self.session.post(
            "https://docs.google.com/forms/u/0/d/e/1FAIpQLSdYvAY6PDOVBl3Bd2FgnkCoz-G0KXk8OV_63gG96FIVYm0mEw/formResponse",
            data=form_data,
        )
        payload = {
            "query": "\n    mutation claimQuestReward($id: ID!) {\n  rewardQuest(id: $id) {\n    count\n  }\n}\n    ",
            "variables": {"id": "1723830082652557313"},
        }
        if wait > 0:
            await asyncio.sleep(wait)

        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        if "errors" in response.json():
            raise PixError(response.json())

        return response.json()

    def calculate_price(
        self,
        width=512,
        height=512,
        sampling_steps=28,
        batch_size=1,
        upscale=1.0,
        model_type="sd",  # "sd", "sdxl", "sd3medium", "dit"
        base_price=400,
        base_step=28,
        control_nets=0,
        enable_adetailer=False,
        priority=1000,  # デフォルトは1000（HighPriority）
        is_img2img=False,
        strength=0.7,
        enable_tile=False,
        sampler_multiplier=1.0,
        email_verified=False,
    ):
        """
        画像生成の価格を計算

        Args:
            width: 画像の幅
            height: 画像の高さ
            sampling_steps: サンプリングステップ数
            batch_size: バッチサイズ
            upscale: アップスケール倍率
            model_type: モデルタイプ ("sd", "sdxl", "sd3medium", "dit")
            base_price: ベース価格
            base_step: 基準ステップ数（デフォルト28）
            control_nets: ControlNetsの数
            enable_adetailer: ADetailerを使用するか
            priority: 優先度 (0=通常, 1000=高(デフォルト), 1500=最高)
            is_img2img: img2imgモードか
            strength: img2imgの強度
            enable_tile: タイルモードを使用するか
            sampler_multiplier: サンプラーの倍率
            email_verified: メール認証済みか（バッチサイズ>1で50%割引）

        Returns:
            int: 最終価格
        """

        # ベース価格の調整
        current_price = base_price

        if model_type == "dit":
            if is_img2img:
                current_price = base_price * 2
            else:
                is_standard = (width, height) in [
                    (768, 1280),
                    (1280, 768),
                    (1024, 1024),
                ]
                is_standard_steps = 20 <= sampling_steps <= 25
                current_price = base_price * (
                    1.5 if is_standard and is_standard_steps else 1.6
                )

        # モデルタイプ倍率
        model_multipliers = {"sdxl": 1.25, "sd3medium": 1.625, "dit": 1.25}
        if model_type in model_multipliers:
            current_price *= model_multipliers[model_type]

        # サイズ倍率
        if not enable_tile:
            size_power = (width * height * upscale * upscale) / (512 * 512)
            current_price *= size_power

        # ステップ数倍率
        if is_img2img:
            effective_steps = 1 + strength * sampling_steps
        else:
            effective_steps = sampling_steps
        step_power = effective_steps / base_step
        current_price *= step_power

        # サンプラー倍率
        current_price *= sampler_multiplier

        # ControlNets
        if control_nets > 0:
            current_price *= 1.4 ** (control_nets - 1)

        # 100単位で切り捨て
        current_price = math.floor(current_price / 100) * 100

        # バッチサイズ
        current_price *= batch_size

        # アップスケール（Hires fix）
        if upscale > 1 and not enable_tile:
            # アップスケール用の追加計算
            upscale_base = base_price if model_type != "dit" else base_price * 1.25
            upscale_price = (
                upscale_base * (width * height * upscale * upscale) / (512 * 512)
            )
            upscale_price *= effective_steps / 28
            upscale_price *= sampler_multiplier
            upscale_price = math.floor(upscale_price / 100) * 100

            # アップスケール価格を追加（50%割引）
            current_price += upscale_price * 0.5

        # ADetailer
        if enable_adetailer:
            adetailer_price = base_price * (1 + 0.8 * sampling_steps) / 28
            adetailer_price = math.floor(adetailer_price / 100) * 100
            current_price += adetailer_price

        # ベース価格を引く
        current_price -= base_price * batch_size

        # メール認証割引（バッチサイズ>1の場合のみ）
        if email_verified and batch_size > 1 and current_price > 0:
            current_price *= 0.5

        # 最低価格・最大割引
        if model_type == "dit":
            current_price = max(current_price, 1000)
        else:
            current_price = max(current_price, 200)

        current_price = max(current_price, -800)

        # 優先度料金
        if priority >= 1000:
            current_price += priority

        return int(current_price)

    async def get_models(self) -> List[Model]:
        models = []

        payload = {
            "query": "\n    query listGenerationModels($before: String, $after: String, $first: Int, $last: Int, $orderBy: String, $tag: String, $type: GenerationModelType, $types: [GenerationModelType], $timeRange: DateRange, $keyword: String, $feed: String, $authorId: ID, $category: String, $loraBaseModelTypes: [GenerationModelType!], $loraBaseModelIds: [ID!]) {\n  generationModels(\n    before: $before\n    after: $after\n    first: $first\n    last: $last\n    orderBy: $orderBy\n    tag: $tag\n    type: $type\n    types: $types\n    timeRange: $timeRange\n    keyword: $keyword\n    feed: $feed\n    authorId: $authorId\n    category: $category\n    loraBaseModelTypes: $loraBaseModelTypes\n    loraBaseModelIds: $loraBaseModelIds\n  ) {\n    edges {\n      node {\n        ...GenerationModelPreview\n      }\n      cursor\n    }\n    pageInfo {\n      hasNextPage\n      hasPreviousPage\n      endCursor\n      startCursor\n    }\n    totalCount\n  }\n}\n    \n    fragment GenerationModelPreview on GenerationModel {\n  ...GenerationModelBase\n  loraBaseModelTypes\n  likedCount\n  liked\n  refCount\n  commentCount\n  artworkSafetyScore {\n    safetyScoreSum\n    safetyScoreCount\n  }\n  latestAvailableVersion {\n    ...GenerationModelVersionBase\n    status\n    downloadUrl\n  }\n  tags {\n    ...TagBase\n  }\n}\n    \n\n    fragment GenerationModelBase on GenerationModel {\n  id\n  authorId\n  title\n  mediaId\n  media {\n    ...MediaBase\n  }\n  type\n  category\n  extra\n  createdAt\n  updatedAt\n  isNsfw\n  isDownloadable\n  isPrivate\n  flag {\n    ...ModerationFlagPreview\n  }\n  loraBaseModelTypes\n}\n    \n\n    fragment MediaBase on Media {\n  id\n  type\n  width\n  height\n  urls {\n    variant\n    url\n  }\n  imageType\n  fileUrl\n  duration\n  thumbnailUrl\n  hlsUrl\n  size\n  flag {\n    ...ModerationFlagPreview\n  }\n}\n    \n\n    fragment ModerationFlagPreview on ModerationFlag {\n  shouldBlur\n}\n    \n\n    fragment GenerationModelVersionBase on GenerationModelVersion {\n  id\n  modelId\n  mediaId\n  media {\n    ...MediaBase\n  }\n  name\n  fileUploadId\n  createdAt\n  updatedAt\n  extra\n  loraBaseModelType\n  loraBaseModelId\n}\n    \n\n    fragment TagBase on Tag {\n  id\n  name\n  displayName\n  mediaId\n  createdAt\n  updatedAt\n  extra\n}\n    ",
            "variables": {"feed": "preset", "type": "ANY_MODEL"},
        }
        response = await self.session.post(
            "https://api.pixai.art/graphql", headers=self.headers, json=payload
        )

        if "errors" in response.json():
            raise PixError(response.json())

        edges = response.json()["data"]["generationModels"]["edges"]
        for edge in edges:
            node = edge["node"]

            models.append(
                Model(
                    node["id"],
                    node["latestAvailableVersion"]["id"],
                    node["title"],
                    node["type"].split("_")[0].lower(),
                )
            )

        return models

    async def get_model_version(self, versionId: str):
        payload = {
            "query": "\n    query getGenerationModelByVersionId($id: ID!) {\n  generationModelVersion(id: $id) {\n    ...GenerationModelVersionPreview\n    model {\n      ...GenerationModelBase\n    }\n  }\n}\n    \n    fragment GenerationModelVersionPreview on GenerationModelVersion {\n  ...GenerationModelVersionBase\n  modelType\n  status\n}\n    \n\n    fragment GenerationModelVersionBase on GenerationModelVersion {\n  id\n  modelId\n  mediaId\n  media {\n    ...MediaBase\n  }\n  name\n  fileUploadId\n  createdAt\n  updatedAt\n  extra\n  loraBaseModelType\n  loraBaseModelId\n}\n    \n\n    fragment MediaBase on Media {\n  id\n  type\n  width\n  height\n  urls {\n    variant\n    url\n  }\n  imageType\n  fileUrl\n  duration\n  thumbnailUrl\n  hlsUrl\n  size\n  flag {\n    ...ModerationFlagPreview\n  }\n}\n    \n\n    fragment ModerationFlagPreview on ModerationFlag {\n  shouldBlur\n}\n    \n\n    fragment GenerationModelBase on GenerationModel {\n  id\n  authorId\n  title\n  mediaId\n  media {\n    ...MediaBase\n  }\n  type\n  category\n  extra\n  createdAt\n  updatedAt\n  isNsfw\n  isDownloadable\n  isPrivate\n  flag {\n    ...ModerationFlagPreview\n  }\n  loraBaseModelTypes\n}\n    ",
            "variables": {"id": versionId},
        }
        response = await self.session.post(
            "https://api.pixai.art/graphql", headers=self.headers, json=payload
        )

        if "errors" in response.json():
            raise PixError(response.json())

        generationModelVersion = response.json()["data"]["generationModelVersion"]

        return ModelVersion(
            generationModelVersion["extra"].get("negativePrompts"),
            generationModelVersion["extra"].get("samplingMethod"),
            generationModelVersion["extra"].get("samplingSteps"),
            generationModelVersion["extra"].get("cfgScale"),
        )

    async def get_all_tasks(self):
        payload = {
            "query": "\n    query listMyTasks($status: String, $before: String, $after: String, $first: Int, $last: Int) {\n  me {\n    tasks(\n      status: $status\n      before: $before\n      after: $after\n      first: $first\n      last: $last\n    ) {\n      pageInfo {\n        hasNextPage\n        hasPreviousPage\n        endCursor\n        startCursor\n      }\n      edges {\n        node {\n          ...TaskWithMedia\n        }\n      }\n    }\n  }\n}\n    \n    fragment TaskWithMedia on Task {\n  ...TaskBase\n  favoritedAt\n  artworkIds\n  media {\n    ...MediaBase\n  }\n}\n    \n\n    fragment TaskBase on Task {\n  id\n  userId\n  parameters\n  outputs\n  status\n  priority\n  runnerId\n  startedAt\n  endAt\n  createdAt\n  updatedAt\n  retryCount\n  paidCredit\n  moderationAction {\n    promptsModerationAction\n  }\n}\n    \n\n    fragment MediaBase on Media {\n  id\n  type\n  width\n  height\n  urls {\n    variant\n    url\n  }\n  imageType\n  fileUrl\n  duration\n  thumbnailUrl\n  hlsUrl\n  size\n  flag {\n    ...ModerationFlagBase\n  }\n}\n    \n\n    fragment ModerationFlagBase on ModerationFlag {\n  status\n  isSensitive\n  isMinors\n  isRealistic\n  isFlagged\n  isSexyPic\n  isSexyText\n  shouldBlur\n  isWarned\n}\n    ",
            "variables": {"last": 30},
        }
        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        edges = response.json()["data"]["me"]["tasks"]["edges"]
        mediaids_all = []
        for edge in edges:
            mediaids = []
            payload = {
                "query": "\n    query getTaskById($id: ID!) {\n  task(id: $id) {\n    ...TaskDetail\n  }\n}\n    \n    fragment TaskDetail on Task {\n  ...TaskBase\n  favoritedAt\n  artworkId\n  artworkIds\n  artworks {\n    createdAt\n    hidePrompts\n    id\n    isNsfw\n    isSensitive\n    mediaId\n    title\n    updatedAt\n    flag {\n      ...ModerationFlagBase\n    }\n  }\n  media {\n    ...MediaBase\n  }\n  type {\n    type\n    model\n  }\n}\n    \n\n    fragment TaskBase on Task {\n  id\n  userId\n  parameters\n  outputs\n  status\n  priority\n  runnerId\n  startedAt\n  endAt\n  createdAt\n  updatedAt\n  retryCount\n  paidCredit\n  moderationAction {\n    promptsModerationAction\n  }\n}\n    \n\n    fragment ModerationFlagBase on ModerationFlag {\n  status\n  isSensitive\n  isMinors\n  isRealistic\n  isFlagged\n  isSexyPic\n  isSexyText\n  shouldBlur\n  isWarned\n}\n    \n\n    fragment MediaBase on Media {\n  id\n  type\n  width\n  height\n  urls {\n    variant\n    url\n  }\n  imageType\n  fileUrl\n  duration\n  thumbnailUrl\n  hlsUrl\n  size\n  flag {\n    ...ModerationFlagBase\n  }\n}\n    ",
                "variables": {"id": edge["node"]["id"]},
            }

            response = await self.session.post(
                "https://api.pixai.art/graphql",
                headers=self.headers,
                json=payload,
            )
            if "errors" in response.json():
                raise PixError(response.json())

            if response.json()["data"]["task"]["status"] != "completed":
                mediaids.append(None)
                continue

            try:
                for batch in response.json()["data"]["task"]["outputs"]["batch"]:
                    mediaids.append(batch["mediaId"])
            except Exception:
                mediaids.append(response.json()["data"]["task"]["outputs"]["mediaId"])

            mediaids_all.append(mediaids)

        return mediaids_all

    async def get_latest_task(self):
        payload = {
            "query": "\n    query listMyTasks($status: String, $before: String, $after: String, $first: Int, $last: Int) {\n  me {\n    tasks(\n      status: $status\n      before: $before\n      after: $after\n      first: $first\n      last: $last\n    ) {\n      pageInfo {\n        hasNextPage\n        hasPreviousPage\n        endCursor\n        startCursor\n      }\n      edges {\n        node {\n          ...TaskWithMedia\n        }\n      }\n    }\n  }\n}\n    \n    fragment TaskWithMedia on Task {\n  ...TaskBase\n  favoritedAt\n  artworkIds\n  media {\n    ...MediaBase\n  }\n}\n    \n\n    fragment TaskBase on Task {\n  id\n  userId\n  parameters\n  outputs\n  status\n  priority\n  runnerId\n  startedAt\n  endAt\n  createdAt\n  updatedAt\n  retryCount\n  paidCredit\n  moderationAction {\n    promptsModerationAction\n  }\n}\n    \n\n    fragment MediaBase on Media {\n  id\n  type\n  width\n  height\n  urls {\n    variant\n    url\n  }\n  imageType\n  fileUrl\n  duration\n  thumbnailUrl\n  hlsUrl\n  size\n  flag {\n    ...ModerationFlagBase\n  }\n}\n    \n\n    fragment ModerationFlagBase on ModerationFlag {\n  status\n  isSensitive\n  isMinors\n  isRealistic\n  isFlagged\n  isSexyPic\n  isSexyText\n  shouldBlur\n  isWarned\n}\n    ",
            "variables": {"last": 30},
        }

        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        if "errors" in response.json():
            raise PixError(response.json())

        tasks = len(response.json()["data"]["me"]["tasks"]["edges"])
        query_id = response.json()["data"]["me"]["tasks"]["edges"][tasks - 1]["node"][
            "id"
        ]
        payload = {
            "query": "\n    query getTaskById($id: ID!) {\n  task(id: $id) {\n    ...TaskDetail\n  }\n}\n    \n    fragment TaskDetail on Task {\n  ...TaskBase\n  favoritedAt\n  artworkId\n  artworkIds\n  artworks {\n    createdAt\n    hidePrompts\n    id\n    isNsfw\n    isSensitive\n    mediaId\n    title\n    updatedAt\n    flag {\n      ...ModerationFlagBase\n    }\n  }\n  media {\n    ...MediaBase\n  }\n  type {\n    type\n    model\n  }\n}\n    \n\n    fragment TaskBase on Task {\n  id\n  userId\n  parameters\n  outputs\n  status\n  priority\n  runnerId\n  startedAt\n  endAt\n  createdAt\n  updatedAt\n  retryCount\n  paidCredit\n  moderationAction {\n    promptsModerationAction\n  }\n}\n    \n\n    fragment ModerationFlagBase on ModerationFlag {\n  status\n  isSensitive\n  isMinors\n  isRealistic\n  isFlagged\n  isSexyPic\n  isSexyText\n  shouldBlur\n  isWarned\n}\n    \n\n    fragment MediaBase on Media {\n  id\n  type\n  width\n  height\n  urls {\n    variant\n    url\n  }\n  imageType\n  fileUrl\n  duration\n  thumbnailUrl\n  hlsUrl\n  size\n  flag {\n    ...ModerationFlagBase\n  }\n}\n    ",
            "variables": {"id": query_id},
        }

        try:
            if (
                response.json()["data"]["me"]["tasks"]["edges"][0]["node"]["status"]
                != "completed"
            ):
                return None
        except Exception:
            return None

        mediaids = []
        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )

        try:
            for batch in response.json()["data"]["task"]["outputs"]["batch"]:
                mediaids.append(batch["mediaId"])
        except Exception:
            mediaids.append(response.json()["data"]["task"]["outputs"]["mediaId"])

        return mediaids

    async def get_task_by_id(self, query_id: str):
        payload = {
            "query": "\n    query getTaskById($id: ID!) {\n  task(id: $id) {\n    ...TaskDetail\n  }\n}\n    \n    fragment TaskDetail on Task {\n  ...TaskBase\n  favoritedAt\n  artworkId\n  artworkIds\n  artworks {\n    createdAt\n    hidePrompts\n    id\n    isNsfw\n    isSensitive\n    mediaId\n    title\n    updatedAt\n    flag {\n      ...ModerationFlagBase\n    }\n  }\n  media {\n    ...MediaBase\n  }\n  type {\n    type\n    model\n  }\n}\n    \n\n    fragment TaskBase on Task {\n  id\n  userId\n  parameters\n  outputs\n  status\n  priority\n  runnerId\n  startedAt\n  endAt\n  createdAt\n  updatedAt\n  retryCount\n  paidCredit\n  moderationAction {\n    promptsModerationAction\n  }\n}\n    \n\n    fragment ModerationFlagBase on ModerationFlag {\n  status\n  isSensitive\n  isMinors\n  isRealistic\n  isFlagged\n  isSexyPic\n  isSexyText\n  shouldBlur\n  isWarned\n}\n    \n\n    fragment MediaBase on Media {\n  id\n  type\n  width\n  height\n  urls {\n    variant\n    url\n  }\n  imageType\n  fileUrl\n  duration\n  thumbnailUrl\n  hlsUrl\n  size\n  flag {\n    ...ModerationFlagBase\n  }\n}\n    ",
            "variables": {"id": query_id},
        }
        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        if "errors" in response.json():
            raise PixError(response.json())

        try:
            if response.json()["data"]["task"]["status"] != "completed":
                return None
        except Exception:
            return None

        mediaids = []
        try:
            for batch in response.json()["data"]["task"]["outputs"]["batch"]:
                mediaids.append(batch["mediaId"])
        except Exception:
            mediaids.append(response.json()["data"]["task"]["outputs"]["mediaId"])

        return mediaids

    async def generate_image(
        self,
        prompts: str,
        negative_prompts: str = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, quality bad, hands bad, eyes bad, face bad, normal quality, jpeg artifacts, signature, watermark, username, blurry, artist name\n",
        sampling_steps: int = 25,
        sampling_method: str = "Euler a",
        cfg_scale: int = 6,
        priority: int = 1000,
        width: int = 768,
        height: int = 1280,
        model_id: str = "1709400693561386681",
        x4: bool = False,
    ):
        payload = {
            "query": "\n    mutation createGenerationTask($parameters: JSONObject!) {\n  createGenerationTask(parameters: $parameters) {\n    ...TaskBase\n  }\n}\n    \n    fragment TaskBase on Task {\n  id\n  userId\n  parameters\n  outputs\n  status\n  priority\n  runnerId\n  startedAt\n  endAt\n  createdAt\n  updatedAt\n  retryCount\n  paidCredit\n  moderationAction {\n    promptsModerationAction\n  }\n}\n    ",
            "variables": {
                "parameters": {
                    "prompts": prompts,
                    "extra": {},
                    "negativePrompts": negative_prompts,
                    "samplingSteps": sampling_steps,  # ↑nsfwは消した、みんないらないよね？ (By たか)
                    "samplingMethod": sampling_method,
                    "cfgScale": cfg_scale,
                    "seed": "",
                    "priority": priority,
                    "width": width,
                    "height": height,
                    "clipSkip": 1,
                    "modelId": model_id,
                    "controlNets": [],
                }
            },
        }
        if x4:
            payload["variables"]["parameters"]["batchSize"] = 4

        response = await self.session.post(
            "https://api.pixai.art/graphql",
            headers=self.headers,
            json=payload,
        )
        if "errors" in response.json():
            raise PixError(response.json())

        return response.json()["data"]["createGenerationTask"]["id"]
