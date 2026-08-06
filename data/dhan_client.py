Your code is probably doing something like:

oc_data = response
logger.info(type(oc_data))
logger.info(oc_data.keys())

Instead, you need to inspect response["data"].

Replace your debugging code with this
response = self.dhan.option_chain(
    NIFTY_ID,
    "IDX_I",
    expiry_date
)

logger.info(f"Full Response = {response}")

if response.get("status") != "success":
    logger.error("Option Chain API Failed")
    return None

data = response.get("data")

logger.info(f"Type(data): {type(data)}")
logger.info(f"Data: {data}")

if isinstance(data, dict):
    logger.info(f"Data Keys: {list(data.keys())}")
I want to see this output

I'm specifically looking for something like:

Data:
{
   "oc": {...}
}

or

Data:
{
   "records": [...]
}

or

Data:
{}

or

Data:
[]

That will tell us exactly how to parse it.

I also suspect one more possibility

Your expiry is:

2026-08-11

If that expiry has no listed option chain (for example, if it's not a valid exchange expiry), some APIs return:

{
    "status": "success",
    "data": {}
}

which would also produce:

Rows parsed: 0

So after printing response["data"], also log:

logger.info(f"Expiry Used: {expiry_date}")
