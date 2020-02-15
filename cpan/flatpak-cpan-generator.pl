#!/usr/bin/env perl

use v5.14;

use strict;
use warnings;

use Config;
use Digest::SHA;
use File::Spec;
require File::Temp;
use File::Temp ();

use Getopt::Long::Descriptive;
use JSON::MaybeXS;
use LWP::UserAgent;
use MetaCPAN::Client;
use Pod::Simple::SimpleTree;


sub scan_deps {
  my ($root) = @_;
  my $localpath = File::Spec->join($root, 'lib', 'perl5', $Config{archname}, 'perllocal.pod');

  my $parser = Pod::Simple::SimpleTree->new;
  my $doc = $parser->parse_file($localpath)->root;

  my @deps = ();

  die "unexpected document root $doc->[0]" if $doc->[0] ne 'Document';

  my $current_module;

  for (my $i = 2; $i < @$doc; $i++) {
    my $node = $doc->[$i];
    if ($node->[0] eq 'head2' && $node->[3]->[0] eq 'C' && $node->[3]->[2] eq 'Module') {
      push @deps, { name => $node->[5]->[2], version => '' };
    } elsif ($node->[0] eq 'over-bullet') {
      for (my $j = 2; $j < @$node; $j++) {
        my $item = $node->[$j];
        if ($item->[0] eq 'item-bullet' && $item->[2]->[0] eq 'C' &&
            $item->[2]->[2] =~ /^VERSION: (.*)$/) {
          $deps[-1]->{version} = $1;
        }
      }
    }
  }

  @deps
}

sub get_url_sha256 {
  my ($url) = @_;

  my $state = Digest::SHA->new(256);
  my $ua = LWP::UserAgent->new;

  my $resp = $ua->get($url, ':read_size_hint' => 1024,
                      ':content_cb' => sub {
                        my ($data) = @_;
                        $state->add($data);
                      });

  die "Failed to get sha256 of $url: @{[$resp->status_line]}\n" if !$resp->is_success;
  $state->hexdigest;

}
sub get_source_for_dep {
  my ($cpan, $dep, $outdir) = @_;
  my $release_set = $cpan->release({
    all => [
      { distribution => $dep->{name} =~ s/::/-/gr },
      { version => $dep->{version} },
    ],
  });

  die "Unexpected @{[$release_set->total]} releases for $dep->{name}\@$dep->{version}"
    if $release_set->total != 1;
  my $release = $release_set->next;

  my $url = $release->download_url;
  my $sha256 = get_url_sha256 $url;

  {
    type => 'archive',
    url => $url,
    sha256 => $sha256,
    dest => "$outdir/@{[$release->distribution]}",
  };
}

sub write_module_to_file {
  my ($output, $root) = @_;

  my $serializer = JSON::MaybeXS->new(indent => 1, space_after => 1);
  my $json = $serializer->encode($root);

  open my $fh, '>', $output or die "Could not open $output for writing\n";
  print $fh $json;
  close $fh;
}

sub main {
  my ($opts, $usage) = describe_options(
    'flatpak-cpan-generator %o <packages...>',
    ['output|o=s', 'The generated sources file', { default => 'generated-sources.json' }],
    ['dir|d=s', 'The output directory used inside the sources file', { default => 'perl-libs' }],
    ['help|h', 'Show this screen', { shortcircuit => 1, hidden => 1 }],
  );

  if ($opts->help) {
    print $usage->text;
    exit;
  }

  die "At least one package is required.\n" if @ARGV == 0;

  my $cpan = MetaCPAN::Client->new;

  say '** Installing dependencies with cpanm...';

  my $tmpdir = File::Temp->newdir;
  system ('cpanm', '-L', $tmpdir->dirname, "--", @ARGV)
    and die "cpanm failed with exit status $?\n";

  say '** Scanning dependencies...';

  my @deps = scan_deps $tmpdir->dirname;
  # my @deps = scan_deps 'lib';
  my @sources = ();

  foreach my $dep (@deps) {
    say "** Processing: $dep->{name}";
    my $source = get_source_for_dep $cpan, $dep, $opts->dir;
    push @sources, $source;
  }

  push @sources, {
    type => 'script',
    'dest-filename' => "@{[$opts->dir]}/install.sh",
    commands => [
      map { "cd $_->{dest} && perl Makefile.PL && make install && cd ../.." } @sources
    ],
  };

  write_module_to_file $opts->output, \@sources;
}

main;
