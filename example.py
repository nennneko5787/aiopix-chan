import asyncio

from Pix_Chan import PixAI

pix = PixAI()


async def main():
    await pix.initialize("3740448@hanntyaikanetwork.net", "omglolpassword", login=True)
    print(pix.token)
    print(pix.user_id)
    # await pix.claim_daily_quota()

    model = (await pix.get_models())[0]
    modelVersion = await pix.get_model_version(model.latestVersionId)

    print(
        pix.calculate_price(
            768,
            1280,
            modelVersion.sampling_steps,
            batch_size=4,
            model_type=model.type,
            email_verified=False,
        ),
    )


asyncio.run(main())
