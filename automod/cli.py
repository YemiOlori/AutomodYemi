from rich.table import Table
from rich.console import Console
from rich import box

from .automod import AutoModClient


class AutoMod(AutoModClient):
    def __init__(self):
        super().__init__()

    def get_hallway(self, max_limit=30):

        # Get channels and print
        console = Console(width=180)
        table = Table(show_header=True, header_style="bold magenta", box=box.MINIMAL_HEAVY_HEAD, leading=True)
        table.add_column("speakers", width=8, justify='center')
        table.add_column("users", width=8, justify='center')
        table.add_column("type", width=8)
        table.add_column("channel", width=10)
        table.add_column("club", width=35, no_wrap=True)
        table.add_column("title", style="cyan", width=70)

        feed = self.client.feed()

        channel_list = []
        for feed_item in feed['items']:

            key = feed_item.keys()
            if 'channel' in key:
                channel_list.append(feed_item)

        i = 0
        for channel in channel_list:
            channel = channel['channel']

            i += 1
            if i > max_limit:
                break

            channel_type = ''
            club = ''

            if channel['is_social_mode']:
                channel_type = "social"

            if channel['is_private']:
                channel_type = "private"

            if channel['club']:
                club = channel['club']['name']

            table.add_row(
                str(int(channel['num_speakers'])),
                str(int(channel['num_all'])),
                str(channel_type),
                str(channel['channel']),
                str(club),
                str(channel['topic']),
            )

        console.print(table)

        return

