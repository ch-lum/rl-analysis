import requests
import pandas as pd
import subprocess
import json
from bs4 import BeautifulSoup
import time
from PhysPar import PhysPar
import csv


def scrape_website(url: str, attempts: int = 0) -> requests.models.Response:
    """Scrape the website and return the response.

    Args:
        url (str): String of the website URL.
        attempts (int, optional): Number of iterations it has already tried. Maxes at 3. Defaults to 0.

    Returns:
        Response: Returns the response of the website.
    """

    # Send GET request to the website
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        if attempts > 0:
            print("Success")
        return response
    elif attempts < 3:
        print("Error:", response.status_code, "Trying again.")
        time.sleep(1)
        return scrape_website(url, attempts + 1)
    else:
        # Handle the request error
        print("Error: ", response.status_code, "Failed on:", url)
        return None


def get_mids(url: str, fp: str = "mids.txt", write: bool = False) -> list:
    """Function returns all match ids (mids) given a url of a ballchasing.com group's team-games-stats
    Further, writes to file called fp if write is True.
    RLCS world championship is the following url: https://ballchasing.com/group/world-championship-x30sn40adb/teams-games-stats
    If function returns None, an error had occurred in either scraping or formatting of the HTML

    Args:
        url (str): string of url
        fp (str, optional): destination filepath. Defaults to mids_fp.
        write (bool, optional): if True, will create a .txt file named 'mids.txt' containing the ids. Defaults to False.

    Returns:
        list: a list of match ids.
    """

    xml = scrape_website(url)
    xml.encoding = "UTF-8"
    xml = xml.text.strip()
    if xml is None:
        return None
    soup = BeautifulSoup(xml, "xml")
    table = soup.find("tbody")

    mids = set()
    a_tags = table.findAll("a")
    for a in a_tags:
        mids.add(a.get("href"))

    mids = [mid[8:] for mid in mids]
    if not all(
        [len(mid) == 36 for mid in mids]
    ):  # All mids are 36 characters long. This checks if something got scraped wrong
        return None

    if not write:
        return mids

    with open(fp, "w") as file:
        for mid in mids:
            file.write(mid + "\n")

    return mids


def mids_from_txt(fp: str = "mids.txt") -> list:
    """Reads the file containing the match ids and returns a list of them.

    Args:
        fp (str, optional): filepath of the mids file. Defaults to "mids.txt".

    Returns:
        list: list of match ids.
    """
    with open(fp, "r") as file:
        list_of_strings = file.readlines()

    list_of_strings = [string.strip() for string in list_of_strings]
    return list_of_strings


def download_replay(mid: str, key: str) -> None:
    """Function downloads the .replay file from ballchasing.com (files should be <2MB) given its match id into a folder named 'replays'

    Args:
        mid (str): 36-character long string of the match id
        key (str): API key for ballchasing.com
    """
    url = f"https://ballchasing.com/api/replays/{mid}/file"
    headers = {
        "Authorization": key,
        "Content-Type": "application/octet-stream",
        "Content-Disposition": "attachment; filename='original-filename.replay'",
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # Assuming the filename is provided in the 'Content-Disposition' header
        filename = (
            response.headers.get("Content-Disposition").split("filename=")[1].strip('"')
        )
        filename = "replays/" + filename

        # Save the file
        with open(filename, "wb") as f:
            f.write(response.content)

        print(f"{mid} - Replay file saved as: {filename}")
    else:
        print(
            f"{mid} - Failed to download replay file. Status code: {response.status_code}"
        )

    """
    Takes a .replay file and uses rattletrap to parse it into .json
    Replay should be in a folder titled 'replays'

    :param mid: mid of the replay
    """


def replay_to_json(mid: str) -> None:
    """Takes a .replay file and uses rattletrap to parse it into .json
    Requires rattletrap downloaded and in PATH
    Replay should be in a folder titled 'replays'

    Args:
        mid (str): match id of the replay
    """
    result = subprocess.run(
        f"rattletrap -i replays\\{mid}.replay -o replays\\{mid}.json -c",
        capture_output=True,
        text=True,
    )
    print(f"{mid} - Return code: {result.returncode}")


def create_csv_header(fp: str = "training_data.csv") -> None:
    """Writes the header into the csv file. This function functionally resets the file.


    Args:
        fp (str, optional): Destination filepath for training data. Defaults to 'training_data.csv'.
    """
    schema = [
        "scores_next",
        "ball_av_x",
        "ball_av_y",
        "ball_av_z",
        "ball_lv_x",
        "ball_lv_y",
        "ball_lv_z",
        "ball_loc_x",
        "ball_loc_y",
        "ball_loc_z",
        "ball_rot_x",
        "ball_rot_y",
        "ball_rot_z",
        "ball_rot_w",
        "0car1_av_x",
        "0car1_av_y",
        "0car1_av_z",
        "0car1_lv_x",
        "0car1_lv_y",
        "0car1_lv_z",
        "0car1_loc_x",
        "0car1_loc_y",
        "0car1_loc_z",
        "0car1_rot_x",
        "0car1_rot_y",
        "0car1_rot_z",
        "0car1_rot_w",
        "0car2_av_x",
        "0car2_av_y",
        "0car2_av_z",
        "0car2_lv_x",
        "0car2_lv_y",
        "0car2_lv_z",
        "0car2_loc_x",
        "0car2_loc_y",
        "0car2_loc_z",
        "0car2_rot_x",
        "0car2_rot_y",
        "0car2_rot_z",
        "0car2_rot_w",
        "0car3_av_x",
        "0car3_av_y",
        "0car3_av_z",
        "0car3_lv_x",
        "0car3_lv_y",
        "0car3_lv_z",
        "0car3_loc_x",
        "0car3_loc_y",
        "0car3_loc_z",
        "0car3_rot_x",
        "0car3_rot_y",
        "0car3_rot_z",
        "0car3_rot_w",
        "1car1_av_x",
        "1car1_av_y",
        "1car1_av_z",
        "1car1_lv_x",
        "1car1_lv_y",
        "1car1_lv_z",
        "1car1_loc_x",
        "1car1_loc_y",
        "1car1_loc_z",
        "1car1_rot_x",
        "1car1_rot_y",
        "1car1_rot_z",
        "1car1_rot_w",
        "1car2_av_x",
        "1car2_av_y",
        "1car2_av_z",
        "1car2_lv_x",
        "1car2_lv_y",
        "1car2_lv_z",
        "1car2_loc_x",
        "1car2_loc_y",
        "1car2_loc_z",
        "1car2_rot_x",
        "1car2_rot_y",
        "1car2_rot_z",
        "1car2_rot_w",
        "1car3_av_x",
        "1car3_av_y",
        "1car3_av_z",
        "1car3_lv_x",
        "1car3_lv_y",
        "1car3_lv_z",
        "1car3_loc_x",
        "1car3_loc_y",
        "1car3_loc_z",
        "1car3_rot_x",
        "1car3_rot_y",
        "1car3_rot_z",
        "1car3_rot_w",
    ]

    with open(fp, "w", newline="") as file:
        csv_writer = csv.writer(file)

        csv_writer.writerow(schema)

    print("Header written")


def write_to_csv(data: list, fp: str = "training_data.csv") -> None:
    """Writes the data to the csv file.

    Args:
        data (list): a single row of data to be written to the csv file.
        fp (str, optional): filepath of output training data. Defaults to "training_data.csv".
    """
    with open(fp, "a", newline="") as file:
        csv_writer = csv.writer(file)

        for row in data:
            csv_writer.writerow(row)


def physpar_wrapper(
    mid: str, output_fp: str = "training_data.csv", threshold: float = 0.95
) -> None:
    """Uses physpar to grab every eligible frame of data from a replay and writes it to a csv file.

    Args:
        mid (str): match id of the replay
        output_fp (str, optional): filepath of output training data. Defaults to "training_data.csv".
        threshold (float, optional): Threshold for shaving function in PhysPar. Set to select all rows. Defaults to 0.95.
    """
    fp = f"replays\\{mid}.json"
    game = PhysPar(fp)
    data = game.shave_phys(threshold=threshold)
    write_to_csv(data, fp=output_fp)
    print(f"{mid} - {len(data)} rows added")


def cleaner(mid: str) -> None:
    """deletes the replay and json files of a match id from replays folder

    Args:
        mid (str): match id to delete
    """
    replay_fp = f"replays\\{mid}.replay"
    json_fp = f"replays\\{mid}.json"

    try:
        subprocess.run(["del", replay_fp], shell=True)
        print(f"{mid} - replay deleted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"{mid} - Error: {e} with {replay_fp}")

    try:
        subprocess.run(["del", json_fp], shell=True)
        print(f"{mid} - JSON deleted successfully.")
    except subprocess.CalledProcessError as e:
        print(f"{mid} - Error: {e} with {json_fp}")
