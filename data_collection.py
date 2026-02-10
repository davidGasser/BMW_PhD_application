from rss_parser import RSSParser
from requests import get
from bs4 import BeautifulSoup
import pandas as pd

def make_request(url:str) -> str:
        response = get(url)
        if response.status_code == 200:
            return response.text
        else:
            raise Exception(f"Failed to fetch URL: {response.status_code}")
        
class FeedItem():
    def __init__(self, title, description, link):
        self.title = title
        self.description = description
        self.link = link
        self.content = None
        
    def model_dump(self):
        return {
            "title": self.title,
            "description": self.description,
            "link": self.link,
            "content": self.content
        }
               
    def extract_feed_content(self):
        if self.link:
            try:
                response = make_request(self.link)
            except Exception as e:
                print("Error fetching content from link for title:",self.title, "\nError:", e)
                return
                
            soup = BeautifulSoup(response, 'html.parser')
            for table in soup.find_all('table'):
                table.decompose()
                
            article_text = soup.find(id="article-text")
            cleaned_element = [" ".join(text.split()) for text in article_text.stripped_strings if len(text.strip()) > 1]
            self.content = "\n".join(cleaned_element)
            
        
    def __str__(self):
        return f"Title: {self.title}\nDescription: {self.description}\nContent: {self.content}\nLink: {self.link}"

    

class RSSFeed: 
    def __init__(self, url: str, max_pages: int = 10): 
        self.url = url
        self.max_pages = max_pages
        self.items = self.parse_feed()
        
    def parse_feed(self) -> list[FeedItem]:
        
        # RSS feed reverts to the first page when the max_pages is out of range
        # So we stop if the a page contains the same items as the previous page
        first_title = None
        items = []
        for i in range(1, self.max_pages+1):
            
            print(f"Fetching page {i} of RSS feed...")
            url = self.url if i == 1 else f"{self.url}?page={i}"
            try: 
                response = make_request(url)
            except Exception as e:
                print(e)
                return []
            
            # get items from RSS feed
            rss = RSSParser.parse(response)
            print(f"RSS feed contains {len(rss.channel.items)} items.")
            
            for idx, item in enumerate(rss.channel.items):
                
                #check for repetitive items to stop pagination
                if idx == 0:
                    if not first_title: first_title = item.title.content
                    else: 
                        if item.title.content == first_title:
                            print("Reached end of RSS feed, stopping pagination.")
                            return items
                     
                feed_item = FeedItem(
                    item.title.content, 
                    item.description.content if item.description else "", 
                    item.links[0].content
                )
                print(f"Extracting content for item {idx}: {item.title}")
                feed_item.extract_feed_content()
            
                items.append(feed_item)
            
        return items 
    
    
    def to_parquet(self, file_path: str):
        print(f"Saving {len(self.items)} items to '{file_path}'...")
        data = [item.model_dump() for item in self.items]
        df = pd.DataFrame(data)
        df.to_parquet(file_path, index=False, engine="pyarrow", compression="zstd")


if __name__ == "__main__":
    url = "https://www.press.bmwgroup.com/my/rss/uuid/7326c34c-4039-44db-b3b5-64a7bedf6efd"
    feed = RSSFeed(url)
    feed.to_parquet("bmw_press_releases.parquet")
    
        