import os
import supabase
from dotenv import load_dotenv

load_dotenv()


supabase_app_url = os.getenv("SUPABASE_APP_URL")
supabase_app_s_key = os.getenv("SUPABASE_APP_S_KEY")
supabase_url = os.getenv("SUPABASE_URL")
supabase_s_key = os.getenv("SUPABASE_S_KEY")


def run_query():
    # create supabase client
    client_app = supabase.create_client(supabase_app_url, supabase_app_s_key)

    result = client_app.rpc("__get_ecoregion_from_location", {
        "language": "english",
        "latitude": -49.279795,
        "longitude": 69.201142
    }).execute()
    print(result.data)


if __name__ == "__main__":
    run_query()
