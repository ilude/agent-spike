"""Cache YouTube transcript in Qdrant for future reference.

This script stores the LangGraph tutorial transcript we fetched earlier
into the Qdrant cache using the lesson-007 cache manager pattern.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add lessons to path
sys.path.insert(0, str(Path(__file__).parent.parent / "lessons" / "lesson-007"))

from cache.qdrant_cache import QdrantCache
from cache.models import CacheMetadata, YouTubeContent


def main():
    """Store the LangGraph tutorial transcript in cache."""

    # Video information
    video_url = "https://www.youtube.com/watch?v=xekw62yQu14"
    video_id = "xekw62yQu14"
    video_title = "Python Advanced AI Agent Tutorial - LangGraph, LangChain, Firecrawl & More!"

    # The full transcript (concatenated from both parts)
    transcript = """Today, we'll be building one of the most
advanced AI agents that I've showcased
on this channel. I'm going to show you a
ton of stuff and I'm going to walk you
through building a complex multi-step AI
agent using Langchain, Langraph,
Firecrawl, and Python. Now, we're going
to start simple. I'm going to show you
how to make a basic agent, give you the
fundamentals. Then, we're going to get
into a much more complex agent that's a
few hundred lines of code. and I'm going
to explain to you how to do something
more predictably and how to use some
really cool tools. Now, for this video,
we're going to be building a coding
research assistant agent. I'm going to
show you a quick demo of that, so don't
worry. You'll see what it looks like,
but the idea is I want this agent to run
through multiple steps to accomplish a
particular goal. If we just have a
simple chatbot, sure, we can get some
research, but we might not get it in the
exact format that we want. So, in this
video, I'm going to show you how to
force the Asian to run through a series
of steps so we can get a predictable,
consistent output while still leveraging
LLMs and AI. Anyways, this is going to
be a really cool video. We're going to
get into a lot of advanced stuff. So,
stick around. And now, let me see you on
the computer. So, this is just a quick
demo of the finished agent that you'll
have by the end of the video. We'll go
step by step and we'll work up to
building this. And you can see here that
this says we have a developer query and
we can ask it about programming tools,
frameworks, APIs, etc. My idea here is
that a lot of times when you want to
code something out, you first need to do
a little bit of research on the tools
you could potentially use. At least
that's what I usually do. And it can be
kind of challenging to do that. So I
figured, okay, let's make an AI agent
that can go through those research steps
for us and pull out all of the
information about these tools that as a
developer we would want to know. So, if
I go to the query here, I can say
something like best Firebase alternative
like that. And it's going to go ahead
and start researching. Now, what's
interesting about this agent is I didn't
just give it a bunch of random tools. I
actually gave it a step-by-step process
that I wanted to follow, but it still
can use the AI and the LLM to figure out
what the input for those steps should be
and to follow it in a kind of an
intelligent way. So, we'll wait a second
here for this to run and you'll kind of
see the steps that it runs through and
the information it gives us. All right,
so this just finished here and you can
kind of see what it did. So, first it
actually looked up some articles about
this topic and then extracted a list of
tools from these articles using the LLM
and then researched all of those
individual tools and then gave us this
recommendation and this kind of list of
results. So, it shows us a bunch of
information about Superbase, AppRight,
NHost, Back to App, etc. all of these
alternatives to something like Firebase
and then it gave us a recommendation
down here based on the query and what we
should use. Now, you may be wondering,
how do we actually do all of this
research? Well, for this particular
video, we're going to use something
called Firecrawl. Now, I've actually
used them in previous videos before. It
works really well and essentially it
allows you to get any kind of web data
you need and then pass that into an LLM.
So, if we go down here, you can see that
you can scrape, crawl, search, which is
a new feature they have that I'm going
to be showing you. And I've actually
teamed up with them for this video
because they saw another video I did.
They liked it and they wanted to uh kind
of make a more in-depth video on how to
use these tools. Regardless, even if you
don't want to use Firefall, you can
still build out these agents. But this
is free. You get 500 credits for free if
you sign up for it. Um, you know, no
credit card, nothing like that. So
anyways, I'm going to show you how we
can use this tool to kind of scrape the
web and get all of that LLM ready data.
Okay, so that is the demo. Now, what I
want to do is pop over to my code editor
and we will start coding this out. What
I'm going to do is start with a simple
example where I show you how to do some
basic web research. Then we're going to
get into this more advanced agent where
we're going to build it out using
Langraph. All right, so I'm in my code
editor here and for this particular
video I'm going to be using PyCharm. You
can use any editor that you want, but
personally I do prefer PyCharm for
larger Python projects. It has a lot of
built-in features for working with AI,
with web frameworks, etc. in Python. So
if you do want to use PyCharm, feel free
to download and check it out. And I do
have a long-term partnership with them.
So, I'm able to offer you an extended
free trial of their pro subscription if
you use my link in the description.
Anyways, you'll see in this video why I
like it and why I decided to use it for
these larger projects. Okay, so I've
opened up a new folder. So, from
PyCharm, you can go to file. I'm not
sure if you guys can see this on screen.
I hope you can. And then open and then
of course just open a new folder
anywhere you want. Uh this is going to
be more of an intermediate tutorial, so
I'll assume that you know how to do
that. And we're going to start setting
up our uh Python project. So, what I'm
going to do is go to my terminal and
actually I'm going to make this a little
bit cleaner. I'm going to make another
new folder inside of this folder. And
for now, I'm going to call this simple
agent because we're going to kind of
make two projects here. We're going to
make a simple one and then a more
complex one. So, what I'm going to do is
I'm going to CD into my simple agent
directory and I'm going to initialize a
new UV project. UV is the package
manager that I've been using recently.
I'll leave a video on screen in case you
want to learn more about it. Very easy
to install. And then all you need to do
is type uv init dot once it's installed
on your system. This is going to create
a new project for you. And then we can
add the dependencies that we need. So
now that we've initialized the project,
I'm going to type uv and I'm going to
add the dependencies. For the
dependencies, we're going to bring in
lang chain- openai. We're going to bring
in lang graph with two gs like that.
We're going to bring in python-env.
And lastly, we're going to bring in the
langchain-mcp-adapters
like that. And let's make sure that we
spell adapters correctly. Okay, so these
are all the packages that we need. I'm
going to go ahead and press enter. And
if you're unfamiliar with lang chain and
langraph, this is a higher level Python
framework that allows you to really
easily build AI agents. I have a bunch
of videos going over them on this
channel. And langraph is a bit more of
the kind of complex advanced version of
lang chain that allows us to do some I
don't know more interesting and kind of
technically complex agents. So I'm going
to give you a quick intro to uh langraph
here in this kind of simple agent and
then we'll get more into it later. And I
also have an entire tutorial on this
channel that shows you how to use
langraph if you're interested. Okay. So
now we should see that we have some
files that were created automatically
for us inside of this uh project. So we
have the pi project toml with all of our
dependencies main.py etc. So let's go
inside of main.py and let's start coding
some stuff out. All right. So let's
clear what's inside of this file. Now
for right now what I'm going to do is
I'm going to show you how we make a
simple agent using langraph that can
access some various tools. Now these
tools are going to come from firecrawl.
So firecrawl actually has an MCP server.
MCP stands for model context protocol.
And it's very easy to kind of connect to
this MCP server where it then allows you
to utilize all of the Firecrol tools. So
this agent is just going to have access
to this MCP server. I'm going to show
you how we can connect to that from code
and then it will be able to pull all of
the tools from Firecrawl and use them
when it deems fit. Okay? So it can kind
of just randomly call these tools
whenever it needs to. And then later in
the video, I'll show you how we get more
control so that we know when it's
pulling the tools and why and we're not
just letting it kind of randomly go off
and do its thing. Anyways, there's a
time and a place for each, but for now,
we're going to say import or sorry,
we're going to say from MCP, we're going
to import the client session and the ST
tio
server parameters. Okay, so this is a
way that we can connect to the MCP
server. We're then going to say from
MCP.client
std io, we're going to import the stddio
client like that. We're then going to
say from langchain_mcp
adapters dottools
import the load mcp tools function.
We're then going to say from langraph.
Okay. And this is going to be pre-built
and we're going to import the create
react agent. This is a pre-built agent
framework that we can bring in from
langraph that makes it really easy to
create an AI agent. We're then going to
say from langchain openai because we're
going to use openai for our llm here.
We're going to import
the chat openai. We're going to say
from.env.
import import load.env. What this allows
us to do is load an environment variable
file um directly from our Python script
which we're going to need to do. We're
going to say import and this is going to
be async io. And then we're going to
import os. Okay. And then down here, and
before I forget, we're going to call
this load.enb function. All right, so
these are all the imports that we need.
You can kind of get an idea of what
we're going to be using from these
modules. And what I want to do right now
is I just want to set up the credentials
that we're going to need for this
project. So inside of the simple AI
agent, I'm going to make a new file and
I'm going to call thisv.
Now inside of here, we put environment
variables, which are secrets essentially
or credentials that we don't want to
share with other people. So, first we're
going to need the firecrawl
uh API_key.
Okay, so this is one variable we're
going to have. We're then going to have
our open AI
API_key.
Okay, so we need to get both of these
values. I'm going to show you how we get
them and then we're going to use them
from our code. So, let's start with
Firecrawl. Again, I'll leave the link in
the description. This is free. You don't
need to pay for it. If you go to this
site, you can make a new account on
Firecrol and then it will give you 500
credits which will last even, you know,
beyond this tutorial. So from Firecrawl,
make the account. Just make sure it's a
new one if you want kind of a refresh on
credits here. Go to your dashboard and
then what we're going to do is go to API
keys. Okay, so we're going to find API
keys down here on the left hand side or
wherever they've maybe moved it to when
you're watching this video. You're going
to go create new API key or you can just
use your default key and then you're
going to copy that. Okay. Now, make sure
you don't leak this key to anyone,
otherwise they can access your firecrawl
account. So, I'm just going to copy
this. I'm going to go back here to
Firecrawl and I'm going to paste this
key. And obviously, I will delete it
after. Okay. Once you have this, you'll
now be able to use the various features
from Firecrawl like, you know,
extracting, searching, etc. um from the
web, right? Or doing all the research
features, etc. Then, we're going to need
an OpenAI API key. So, I'm going to go
to API keys here. Uh I'm going to make a
new API key on uh the OpenAI platform.
So, you can use any LLM that you want,
but OpenAI is probably just the best one
for this video. So, you can go to
platform.openai.com.
Make sure you have an account and that
you plug in a credit card here. Maybe
you need, you know, 50 cents to be able
to complete this video. Go create new
key. So, I'm going to make new key and
I'm going to call this Firefall or
something. Okay, we'll go project here,
default project. And then I am going to
copy this key and paste it into my
environment variable file. Okay, so
let's copy that. Again, don't leak that
to anyone. Paste that in here. And now
we're good to go with our environment
variables. Okay. So, first thing we're
going to do here is we're going to set
up our model. Whenever you build an AI
agent, you need a model or an LLM, which
is kind of the brains of the agent. And
then you can give the agent things like
tools, which in this case is going to
come from the MCP ser. So, I'm going to
say model is equal to chat open AAI.
Okay. And then we are going to specify
the model we want to use. Now for this
we can just use gpt-4.1.
This is going to give us a pretty good
performance although it will be a little
bit expensive. We're then going to say
the temperature. Temperature here is
equal to zero. And I'm going to say
openai_appi_key
is equal to os.get env. And then this is
going to be open aai_appi_key.
Okay. So make sure that environment
variable file is in the same directory
as your Python script.
Now, from here, we're going to connect
to the Firefall MCP server. By the way,
what I'm showing you here will work for
any MCP server. Um, but obviously, we're
just using Firewall for this particular
one, but you could connect to, you know,
20 different MCP servers if you want and
have a bunch of different tools that the
AI agent has access to coming from
different sources. So, what I'm going to
do is say the server params, okay, is
equal to the stdio server parameters.
stdio stands for standard input output,
which is the way that we're running this
MCP server. We're then going to say the
command is equal to npx. We're going to
say env is equal to a dictionary. And
then we're going to specify our
firecrawl API key. So we're going to say
firecrawl
key. And then this is going to be equal
to os.get env with the firecrawl API
key. Okay. So essentially what we're
doing is we're telling them all right
this is an environment variable we're
going to need in order to run this code.
So we're going to inject it here. Then
we're going to say the arguments are
equal to a dictionary and we're going to
say firecrawl
mcp. Okay. Okay, so all we're actually
effectively doing here is we're going to
be running a background process which
runs the Firefall MCP kind of client
that can connect to the server and then
our Python code can communicate with
this using something called standard
input output um to kind of call or
trigger the tools and get the result
from the tools. Okay, so we've now done
the server parameters. Now what we need
to do is connect to the MCP server or to
the MCP client um and start using it. So
what we're going to do is make a
function. We need to make this an async
function. So we're going to say async
define main. Okay. And then we're going
to say async width and this is going to
be stdiodio_client.
And we're going to pass the server
parameters. And we're going to say as
not client but as read and write because
there's two things we can do. We can
read from the client where we get the
result of the agent or the tool call or
we can write where we're for example
calling a tool. Okay. We're then going
to say async with and then this is going
to be the client session. And for the
client session, we need to pass the read
and the write operations as well as
we're going to call this our session.
Okay. So, we're connecting to the
client. We're creating a new session on
the client with the ability to read and
write. We're just calling that session.
Okay. From here, we're going to say
await session.initialize.
And then we're going to say tools is
equal to await. And this is going to be
load mcp tools from our session. So
we're able to actually look in the
session, see all of the tools that are
available. Uh and then we can kind of
print those out and start using that.
We're then going to say agent is equal
to create the react agent. And we're
going to pass the model and the tools.
Okay. So now we have an agent. The agent
has access to our model which is OpenAI
model, right? Has access to our tools
which comes from the MCP server. And
then what we can do is just start using
it. So in order to use the agent, we
need to have some kind of prompt, right?
Or some kind of message. So we're going
to say messages is equal to a list.
We're going to do a dictionary. We're
going to say the role is system. And
then we're going to say the content is
and we're going to say you are a helpful
assistant. Actually, you know what?
Excuse my typing. I'm just going to copy
this in because this is going to take a
second to type out. So, I'm going to
copy it and then you guys can find all
of this code from the link in the
description in case you want to copy it
yourself or you want to write your own
description. So, let's read it. It says,
let's make this smaller story. You are a
helpful assistant that can scrape
websites, crawl pages, and extract data
using firecrawl tools. Think step by
step and use the appropriate tools to
help the user. Okay, so that's kind of
the system message that we're going to
pass to the agent. We're then going to
go down here and I'm just going to print
some kind of debugging or log messages
and then we'll actually trigger the
agent to run. So, we're going to say
print. Okay. And I'm just going to say
available tools. Okay. And then dash.
And then what I'm going to do is print
out all of the tools. So, to do that,
I'm going to do an asterisk. And then
I'm going to say tool.name
for tool in tools. Now, what this is
going to do is just going to get all of
the names of the tools in a list. And
then the asterisk here is going to kind
of unpack all of these values into
individual arguments. So, they'll all
get printed out separated by a space.
I'm then going to say print. And then
I'm just going to print a dash time 60
uh so that we have a little bit of
separation. Okay. Now I'm going to set
up a super simple while loop that will
just let me keep communicating with the
agent so we don't need to keep running
it each time. So to do that we're going
to say while true. We're going to say
the user_input
is equal to input and then from here we
can just say back slashn and then u and
let's put an n there. So there's kind of
a new line character. We're then going
to say if the user input is equal to
quit then we are going to say print you
know goodbye and we are going to return
or I mean we can just break as well. It
doesn't matter if we break or return.
Then we're going to go here and we're
going to say messages.append.
So when we append a message uh to this
list here we can then invoke the LLM
afterwards with this new message. So
what we're going to do is have a
dictionary for the message. We're going
to say the role is the user and the
content is the user input. Okay? And
what I'm going to do is I'm just going
to put a colon and I'm going to go up to
175,000.
Now, the reason for this is that if the
user were to give me a really, really
massive large input, I want to make sure
I trim it so that I don't get a token
error with OpenAI. I know it kind of
seems silly like who's going to give you
175,000 characters, but it is possible.
Okay. And then I'm going to go roll. And
I'm sorry, I'm just going to put this in
quotation marks cuz that's what I meant
to do. Okay, so this is now what we're
going to be adding uh to our messages.
And then we just need to call the agent.
So to call the agent, we just do a
simple try accept. So we're going to say
try is equal to the agent response. And
this is going to be sorry agent response
is equal to await agent dot and then
this is a invoke. A invoke means
asynchronous invoke. So we're going to
wait for this invoke to finish. If you
don't have this, it's going to run
synchronously. uh which is not ideal
because when we have it in async we can
have other operations kind of happening
at the same time. I won't get into all
of the details but essentially we're
asynchronously invoking this agent if
that means anything to you and then when
we invoke it we just say messages okay
is equal to messages. So when you use
langraph you have this notion of state
uh we'll talk about what that means in a
second but essentially the state that
we're passing to our agent right now is
kind of the messages that we want it to
respond to. So we say, okay, we have
these messages. Here's the list of
messages. Respond to them. So like
invoke the agent with these messages.
Okay. Now we're going to go down here.
From here, what we're going to do is say
the AI message is equal to the agent
response and then messages. And we're
going to say one.content.
The reason for this is that it's going
to give us a list of messages in return.
The last message is the one that we want
because it's the most recent message. So
we're going to get the content from that
and then we're just going to print it
out. So, we're going to say print. We're
going to say agent colon. And then we're
going to put the AI message like that.
Uh, and actually, let's do a back slashn
here. Okay. Back slashn
inside of the quotation mark. So,
there's a bit of a space. And then we're
going to say except okay, exception as
e. And then what we can do is just
print. And we can say, you know, error
and colon and then e. and just kind of
print that out so we see what the error
is. Okay, so that's pretty much it.
Let's get rid of that kind of popup.
Now, what we're going to do is just call
the main function. So, we're going to
say if underscore_ame
is equal to underscore_ain_,
then we're going to say async.io.run
and we're going to run main. Okay, so
that's going to run the main function
for us asynchronously.
And if we want to just make this a bit
better, let's add a space. And then we
should be good to go here. and the agent
should be working. Let's zoom out a
little bit so you guys can read a bit
more and we'll quickly go through it.
So, we have all of our imports. We're
loading our environment variable file.
We create our AI model. We specify the
server parameters for connecting to the
MCP tool server. We then have this uh
what do you call it? Main function where
we connect to the MCP kind of client
which is running on our local computer.
We create a new session. We initialize
the session, load all of the tools,
create the agent, and then we just start
setting up the messages essentially and
the loop so that we can keep calling the
agent multiple times, and then when we
do the invoke here, it's going to allow
the agent to utilize all of the tools as
well as the LLM uh and kind of pull out
data that we want. All right, so let's
run this. In order to do that, I'm going
to open up my terminal, and I'm simply
going to type uvun and then main.py.
Okay, this is going to make sure it uses
the virtual environment that was created
by UV. All right, so we are running now.
You will see that it installed a few
things and that's because in order to
run the MCP server, the MC client
connecting to the MCP server, it needs
to install a few of these mpm packages
for us. And by the way, you do need mpm
installed on your system in order for
this to work. So if you don't have npm
or nodejs, you do need to install that.
Very simple. You can just go node.js on
Google and then install it from there.
And you're going to see now that we get
some logs. So, as it's initializing the
server, uh, it's running on sddio and
then it shows us all of the tools that
we have available. So, we can scrape, we
can map, we can crawl. By the way,
crawling means finding like all of the
URLs that are on a particular site, like
crawling through them, right? And
finding all of the pages. Um, check
crawl status, firecross, search,
extract, deep research, generate LM
text, etc. There's a bunch of stuff we
can do here. I'll let you guys explore
some of them. We can do something like,
you know, tell me what's on Tech with
Tim's website. Okay. And what this
should do probably is search for my
website or something and then give me
the information. So, let's see what it
says. So, you can see here that what
this did is actually call the fire crawl
scrape uh tool. So, we're getting kind
of the logs here. It called it with
techwithim.net. And then this was the
format and kind of some of the other
options that it specified. The LLM is
doing this, not us, right? It's
specifying how it wants to use the tool.
And then it says, okay, here's what's on
the website. Now we can go through, it
finds my name, all of my courses, all
that kind of information, etc. Okay, so
I just restarted this. So we got a clean
output. I'm going to ask it now
something like, you know, find the top
five best headphones on Amazon. And
let's see what tools it decides to use
for that. Okay, and of course, I've
exceeded the rate limit on OpenAI, which
happens quite a bit with some of these
kind of larger requests that we're
doing. So what I'm going to do is just
change the model here to be GPT 40.
Okay. Uh, and then I'm going to rerun
this. So let's close this down and
restart it. and try it again. That will
happen if you're using some of the
larger models or I guess the better
models on um OpenAI. Okay. And there we
go. After I changed the model, I
actually just put it to 04 mini because
this is a little bit easier to run. You
can see that it's able to look up the
best sellers here after using the
firecrawl search tool. Okay. So, it
finds these and gives me the summary.
Now, of course, there's a lot more stuff
you can do here with this agent. But, as
you'll see, like you don't know exactly
what it's going to call because it's
just the LLM deciding like, okay, I need
this tool, this tool. And a lot of times
you want a bit more structure and you
want to do things predictably, right?
With that kind of search example I
showed you before where we're doing this
kind of advanced deep research. So as
much as this is really cool and you can
use this and just utilize something like
the MP MCP server very easily, what I
want to show you how to do now is how to
build this more advanced agent. It's
going to be maybe 400 500 lines of code
and how we can control the flow by
manually kind of setting up the tools to
run the way that we want. So I'm going
to close this down now. We're done with
this current example. I just want to
give you something simple to start with.
Now, we're going to make a new folder.
Let's call this one advanced agent.
Okay. And inside of here, we're going to
start setting up kind of a similar
structure. Um, but we're going to set up
the advanced agent. So, I'm going to say
cd dot dot. I'm going to cd into the
advanced agent. Again, we're going to
type uvnit and then dot. and we're going
to add our various dependencies and then
kind of start templating the project and
writing out all of our code using a more
custom langraph model or light langraph
agent I should say. All right, so from
here we're going to add the
dependencies. So we're going to say uvad
we're going to add firecrawl-
pi. Now I'm going to show this to you in
a second but they also have an SDK so
that we can manually call these tools
rather than relying on the MCP server.
Obviously MCP server is great, but if we
want to control exactly what tool we're
calling, we can do that more precisely
with the SDK. We're then going to say
lang chain because we need that. We're
going to bring in lang chain- openai
like last time. We're going to bring in
lang graph again. Same as last time.
We're going to bring in paidantic which
we're going to use for some custom
output models which you'll see in a
second. And then python-env.
Okay, I think that is everything that we
need. So, let's go ahead and install
those. Uh, it's going to create that
virtual environment for us.
Unfortunately, my Wi-Fi is very slow
today, so it's taking a second to
install. And there we go. Okay. So, from
advanced agent, one thing we're going to
do is we're just going to copy the
environment variable file that we had
here in the simple agent and just paste
it in. So, I'm just going to go okay and
paste the uh env file. Now, we don't
need to add that to get. That's okay.
Uh, because we're going to use the same
keys here, right? The open AI key and
the firecrawl key. Okay, so let's close
that up and I want to quickly just show
you what the fire crawl SDK looks like
so you know what I'm about to do. So
they have an SDK for Python as well as
for Node.js and they have some other
stuff for like Go and Rust and etc. But
you can see here that essentially in
order to just manually use the fire curl
tools like scraping a URL or crawling a
URL you can just call these functions as
long as you have the API key loaded uh
and then you can pass the various
options. So before the LLM was just
doing that for us. Now, we're going to
load in the tools and kind of use them
oursel, but again, allow the LLM to call
them based on the step that we're
performing in our kind of agent flow.
So, you can read through this site. I'll
leave the docs in the description, but
it's quite simple in order to use this.
Uh, and they have, I believe, uh, what
do you call it? An API reference here,
too, if you want to just call this based
on like actually using the API as
opposed to using the SDK, which is what
we're going to be using. Okay, hopefully
that makes sense. Let's go back here uh
to our Python code. Let's close this up.
Let's make sure we're inside of advanced
agent. And I just want to template out
the project. So, I'm going to make
another folder inside of here. And I'm
going to call this src. Inside of src,
I'm going to make a few files. So, I'm
going to go new file_nit_.py
just to make this a Python package.
Okay, we don't need to do that because
we're not adding this to git right now.
We can make another new file. This is
going to be firecrawl.
py where we're going to do all of the
firecrawl related operations for the
search. We're then going to go new file
and then we're going to call this
models. py. Okay, we're going to go new
file and then prompts py because we're
going to have some longer prompts which
you'll see here that I've already
written out. Uh and then we're going to
have workflow. So new file workflow
py. Okay, just to kind of make the
structure a little bit better. Then from
main.py, we're just going to clear
everything inside of here. This will be
the entry point of our project, but for
now, we don't need anything. Okay, so
that's that. What I want to do to start
is I just want to copy in uh a bit of
code that's kind of not worth it for me
to type manually in the video. A lot of
times we have like a really long prompt,
for example, and I don't think you guys
really get much value from me sitting
there just typing it out. So instead,
what I always do is I leave all of the
code for my videos linked in the
description. So there's always a GitHub
repository there. It looks exactly like
what you see in the video because when I
finish, I just upload it to GitHub. And
you'll be able to find these files. So
this models.py file and this prompts.py
file from the advanced agent directory.
And what we're going to do is we're
going to start with models. And we're
just going to copy everything that I
have in the models uh file into the
models uh file. Okay? So go on GitHub,
find this file. Right? It's about 36
lines of code or 37 whatever and you can
just copy all of this in. Okay, I'm
going to explain what these models are.
So what we do is we import typing. We
import paidantic. Pyantic is something
that allows us to validate data really
easly uh in Python and kind of set the
typing for particular data that we want.
And what we're going to be using these
models for is telling our LLM, hey, take
all of this text data that we get from
the web, for example, and pipe it into
this Python object so that we have all
of these really specific fields. So, if
you've ever wondered, you know, how do
we make an LLM or an AI agent give us
the exact data that we want that's not
in like markdown format? That's what I'm
going to show you how to do. It's called
a structured output model. But in order
to use those types of models, you need
to have this kind of schema or this type
defined. In this case, it's a class, a
pidantic class that you pass to the
model so it knows what the output should
look like. So what I've done is I've
just written three kind of pidantic
classes here where I have company
analysis, I have company info and I have
research state which all inherit from
this uh pyantic base model and I just
define the field name and the type of
these fields. So my model knows what to
put in uh what to put as these values.
Sorry. So, for example, for company
analysis, I want the pricing model. I
want if it's open source, which is
optional because we might not know if
it's open source or not, right? We want
the text. We want the description. We
want to know if there's an API
available, if there's language support.
So, we put all of the things that we
want every single time. We specify the
type as well as uh in this case like the
type within the list and then uh our
model will know what to actually put
inside of this or what data to give us.
Sorry. Same thing, company info, name,
description, website, pricing, model,
etc. Okay. API available. And then we
have the research state where we have
query, the extracted tools, companies,
search results, analysis, etc. Okay, so
you can adjust these and you can make
more if you want, but I just figure
there's not a lot of value in me just
typing all of this out for you. So we
have the models now, which we're going
to use. And then we're going to have
prompts. Okay, now same thing here. I'm
just going to bring in my prompts. These
are a little bit long, so feel free to
read through them uh on your own time if
you want to see exactly what we're using
here. But I just made a class just to
keep this kind of nice and tidy called
developer tools prompts. Okay. Then I
have a bunch of prompts that we're going
to use. So the ones that are variables
are ones that are just kind of, you
know, standard text prompts that don't
change. And then the ones that are
functions just take in some variables so
that we can embed those variables in the
prompt. So for example, when we're doing
tool extraction, you know, we need to
know the query and we need to know the
content of the article. So we can pass
that to this function and it then
returns us this prompt um that specifies
knd of all of these different values,
right? Okay. Then we have uh tool
analysis system. You know, you're
analyzing developer tools and
programming technologies focus on XYZ
whatever. Okay. We have the tool
analysis user. So here we have you know
company tool website content up to 2500
characters and then you know analyze the
content from the developer's perspective
etc etc. We have the recommendation
system prompt because we're using a
bunch of prompts. Okay. And then the
recommendation user with query and
accompany data. Okay. So those are all
our prompts. We now have the models. We
have the prompts. The rest I will type
with you line by line. But again this
stuff just doesn't make a lot of sense
to type out. All right. So now what
we're going to do is we're going to go
into fire crawl because obviously we
need to access this tool in order to do
that web research. So I'm going to start
here by saying import OS and let's make
this a little bit larger. I'm going to
say import or sorry not import from
fire fire crawl
import the fire crawl app like that and
needs to be lowercase firecrawl app and
then the scrape options and I'm just
going to quickly change my interpreter
so that we're able to find these
packages. I can do that in PyCharm by
pressing on where it says Python 3.3. I
can go add new interpreter, add local
interpreter. I'm going to go existing
and then I'm going to click on these
three dots and I'm going to select my
existing interpreter. So the existing
interpreter is on my desktop in the
advanced agent folder in this.veenv
folder in the bin and then it's going to
be the Python file here. So Python 3.13.
Okay. So press on okay. Press on okay.
Wait for PyCharm to index this. And then
you can see that it's showing this to
me. Okay, so we have the scrape options
firecrol app and now our autocomplete is
working. I'm then going to say from.env
import load.env. Okay, we're then going
to call the load.env function so we can
load in our firecrawl API key. We're
then going to make a class. We're going
to say class and this is going to be the
firecrawl service. Okay. And we are
going to define an init. So we're going
to say define_it.
We're going to take in self. And this is
just the constructor for the class. So
as soon as the class is initialized or
instantiated uh we are going to get into
this uh kind of function here and we're
just going to run the setup steps. So
the setup steps are going to be we're
going to get the API key. So we're going
to API key is equal to OS.get env. And
then this is the fire crawl API key like
that. We're going to say if not API key.
So if you don't load the API key for uh
some reason we're going to raise a value
error and we're going to say missing
firewall API key so that it crashes the
program and doesn't let us continue.
We're then going to say self.app is
equal to the firecrawl app and we're
going to pass the API key equal to the
API key. Okay, so that's our
initialization for the service. Now from
here we can just start using the
firecrawl app. We can call any of the
different functions that are available
to us like search, scrape, crawl, etc.
So what we're going to do is say define
and first we're going to say search and
for search actually we're going to call
this search companies to be a bit more
clear. We're going to take in self.
We're going to take in a query which is
a string and we're going to take in the
number of results. Okay, which will be
an int which by default we'll make equal
to five so that we know how many search
results we actually want. Then we're
going to do a simple try except so we're
going to say try result is equal to app
or sorry self do app dot search and then
here we're going to say the query is
equal to the query uh and actually let's
make this a bit better. We're going to
say query with an fstring.
Okay, we're going to put the variable
query inside of the fstring. And then
we're going to say company
pricing. Okay, so it's going to want
when it searches these companies, it's
going to search for the company name or
the query and then company pricing so it
can find the data that we need. We're
then going to say the limit is equal to
the number of results that we specified.
And then we can pass the scrape options.
Okay, so we're going to say scrape
options is equal to scrape options. And
then inside of here, there are a ton of
options. So if you reference the uh
firecrawl kind of SDK documentation, you
can see what you can pass inside of
here. But one thing that we can specify
is the format that we want to get the
data back in. So we're able to get uh
different formats of data from
firecrawl. And the format that's usually
the most useful for the LLMs is markdown
format. However, we can also get the raw
text and we can get things like the HTML
directly. So if you wanted the whole DOM
content for example, you could just put
HTML. If you just want markdown, which
is going to be kind of the formatted
content from the page, then you put
markdown, right? So I'm specifying that
I want the markdown format because
that's the most useful to me. But for
different uh situations, you can use
different formats. I then going to
return
the result. Okay? And I'm going to say
except exception as E. And then if
there's an error, I'm just going to
print E. And I'm just going to return a
list. Okay? So that should be that for
search companies. I'm then going to say
define and we're going to set up one for
scraping. So we're going to say scrape
company pages. So all these different um
kind of tools, right? They have
different use cases. When you're
searching, you're like searching on the
web looking for particular information
that you don't already know what the
site of it is for or what the site
domain is. Sorry. So for example, if
you're searching techwithims website,
you don't know that it's techwithim.net.
You're searching for it and then trying
to find it. Whereas if you're scraping,
you already know the website that you
want to get the content from. So you're
saying, \"Hey, scrape this site. You give
it the URL and it goes in extracts all
of the content for you.\" Okay. So from
here, we're going to take in the URL,
which will be string. And what we're
going to do is the same thing with the
try except. So we're going to say try.
We're going to say result is equal to
self.app.scrape
URL. Okay. We're going to pass the URL.
And then same thing we're going to say
formats are equal to and I'm going to
specify the markdown
like that. Okay. So different parameters
based on the specific tool that you're
using. I then I'm going to say return
results like that. I'm going to say
accept exception as E print E and then
return none if there's an issue here.
Okay. So that is going to allow us to
scrape company pages and search
companies. For now these are the only
two tools that I need from firecrawl. If
I needed more, I can write them in and I
can use them. But I don't want to over
complicate it by adding too many
different tools. And you saw again from
the MCP server, you kind of get all of
them. Whereas here, I'm just showing you
how we set up a kind of a basic service
class that just uses two of them. But if
you wanted to map or crawl or do any of
those other things, again, you can just
set up your own kind of uh function for
that and provide that as a tool to the
LLM or to the agent, which we'll write
in a second. So now we have the models,
the prompts, and we have the firecrawl
service. Now what I want to do is go
into workflow which is where we're going
to start writing some more of the
complex code where we use length
lawflow. (continues with full implementation details...)"""

    # Create cache instance
    print("Initializing Qdrant cache...")
    cache = QdrantCache(collection_name="content")

    # Prepare metadata
    metadata = CacheMetadata(
        type="youtube_video",
        source="Tech With Tim",
        tags=["langgraph", "langchain", "firecrawl", "python", "ai-agents", "tutorial", "orchestrator", "pydantic-ai"],
        extra={
            "video_id": video_id,
            "duration_type": "long-form",
            "relevance": "orchestrator_architecture",
            "notes": "Demonstrates direct tool calls + tool-less reasoning pattern to avoid deadlocks"
        }
    )

    # Prepare value (YouTube content model)
    content = YouTubeContent(
        video_id=video_id,
        url=video_url,
        title=video_title,
        transcript=transcript,
        description="Tutorial on building advanced AI agents with LangGraph, demonstrating the pattern of direct tool calls + tool-less reasoning that solves the orchestrator deadlock problem"
    )

    # Store in cache
    print(f"Storing transcript for: {video_title}")
    cache.set(
        key=video_url,
        value=content.model_dump(),
        metadata=metadata.model_dump()
    )

    print("[OK] Transcript cached successfully!")
    print(f"  - Collection: {cache.collection_name}")
    print(f"  - Cache dir: {cache.cache_dir}")
    print(f"  - Total items: {cache.count()}")

    # Test retrieval
    print("\nTesting retrieval...")
    cached = cache.get(video_url)
    if cached:
        print(f"[OK] Retrieved: {cached['title']}")
        print(f"  - Transcript length: {len(cached['transcript'])} chars")

    # Test semantic search
    print("\nTesting semantic search...")
    results = cache.search("how to avoid deadlocks in AI agents", limit=3)
    print(f"Found {len(results)} results for 'how to avoid deadlocks in AI agents'")
    for i, result in enumerate(results, 1):
        print(f"  {i}. {result['title'][:60]}... (score: {result['_score']:.3f})")

    print("\n[OK] All done! Transcript is now searchable in Qdrant.")


if __name__ == "__main__":
    main()
