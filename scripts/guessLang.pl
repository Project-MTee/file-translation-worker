#!/usr/bin/perl -w

use strict;
use Encode::Guess;

if(@ARGV != 2)
{
    print "ERR";
    exit;
}

my $file = $ARGV[0];
my $lang = $ARGV[1];

open(FILE,$file);
binmode(FILE);
if(read(FILE,my $filestart, 5000)) {
    my $enc = guess_encoding($filestart);
    close(FILE);

    if(ref($enc))
    {
        if (open(my $fh, "<:encoding(".$enc->name.")", $file ) )
        {
            while ( my $line= <$fh>)
            {
                if($line =~ /<tuv[^>]*lang="($lang[^"]*)"/i)
                {
                    print $1;
                    close $fh;
                    exit 0;
                }
            }
            close $fh;
        }
    }
    else
    {
        if (open(my $fh, "<", $file ))
        {
            while ( my $line= <$fh>)
            {
                if($line =~ /<tuv[^>]*lang="($lang[^"]*)"/i){
                    print $1;
                    close $fh;
                    exit 0;
                }
            }
            close $fh;
        }
    }
    # print "Encoding of file $file can't be guessed\n";
}
else {
    # print "Cannot read from file $file\n";
    close(FILE);
}

print "ERR"
