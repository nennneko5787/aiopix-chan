import asyncio
from Pix_Chan import PixAI

pix = PixAI()


async def main():
    await pix.initialize("<メールアドレス>", "<パスワード>", login=False)
    print(pix.token)
    print(pix.user_id)
    await pix.claim_daily_quota()
    await pix.claim_questionnaire_quota()

    query_id = await pix.generate_image(
        "<プロンプト>",
    )
    media_ids = await pix.get_task_by_id(query_id)
    for media_id in media_ids:
        print(await pix.get_media(media_id))


asyncio.run(main())
